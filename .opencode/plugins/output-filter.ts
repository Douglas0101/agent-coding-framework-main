import { type Plugin } from "@opencode-ai/plugin"
import { mkdir, readdir, rename, stat, unlink, writeFile } from "node:fs/promises"
import path from "node:path"

import {
  type PatternRule,
  normalizeFlags,
  applyRedactions,
  isSensitiveKey,
  stableStringify,
  sortJsonValue,
} from "../lib/shared"

import { metrics } from "../lib/metrics"

/**
 * Detecta se o output está indo para um terminal interativo (TUI).
 * Quando em modo TUI, o prefixo estruturado corrompe o rendering do cursor.
 *
 * Ordem de precedência:
 *   1. Env var OPENCODE_OUTPUT_FILTER_PREFIX=0 → desabilita prefixo
 *   2. Env var OPENCODE_OUTPUT_FILTER_PREFIX=1 → força prefixo
 *   3. process.stdout.isTTY === true → desabilita prefixo (modo interativo)
 *   4. Default → habilita prefixo (modo CI/pipe)
 */
function isInteractiveMode(): boolean {
  const envOverride = process.env.OPENCODE_OUTPUT_FILTER_PREFIX
  if (envOverride === "0") return true   // suprime prefixo
  if (envOverride === "1") return false  // força prefixo mesmo em TTY
  return process.stdout.isTTY === true
}

const _isInteractive = isInteractiveMode()

type SuppressionRule = {
  max_output_lines: number
  keep_patterns: string[]
  suppress_patterns: string[]
}

type ManifestPhase = {
  status: "pending" | "in_progress" | "complete" | "failed"
  agent: string
  outputs?: string[]
  checksum?: string
  started_at?: number
  completed_at?: number
  current_step?: number
  total_steps?: number
  plan?: string
}

type SessionManifest = {
  session_id: string
  agent: string
  timestamp: string
  directory: string
  phases: {
    exploration: ManifestPhase
    implementation: ManifestPhase
    review: ManifestPhase
  }
  state_hash: string
  resume_capable: boolean
  total_tokens: number
  total_cost: number
  message_count: number
  last_tool_call: string
  created_at: string
  updated_at: string
}

type ManifestConfig = {
  enabled: boolean
  persist_dir: string
  auto_phase_tracking: boolean
  state_hash_enabled: boolean
  max_manifests: number
  atomic_write: boolean
}

type OutputFilterConfig = {
  enabled: boolean
  max_output_chars: number
  redaction_patterns: PatternRule[]
  suppression: Record<string, SuppressionRule>
  enrichment: {
    include_structured_summary: boolean
    include_by_category: string[]
    detect_complexity: boolean
    detect_leetcode_patterns: boolean
    detect_anti_patterns: boolean
  }
  examination: {
    sequential_plan_prompt: boolean
    auto_examine_on_edit: boolean
    auto_examine_on_test_failure: boolean
    leverage_engineering_baseline: boolean
  }
  manifest: ManifestConfig
}

const DEFAULT_MANIFEST_CONFIG: ManifestConfig = {
  enabled: true,
  persist_dir: ".opencode/manifests",
  auto_phase_tracking: true,
  state_hash_enabled: true,
  max_manifests: 20,
  atomic_write: true,
}

const DEFAULT_CONFIG: OutputFilterConfig = {
  enabled: true,
  max_output_chars: 12000,
  redaction_patterns: [
    { label: "openai_key", pattern: "(sk-[a-zA-Z0-9]{20,})", flags: "g", replacement: "[redacted-openai-key]" },
    { label: "aws_access_key", pattern: "(AKIA[0-9A-Z]{16})", flags: "g", replacement: "[redacted-aws-key]" },
    { label: "github_pat", pattern: "(ghp_[a-zA-Z0-9]{36})", flags: "g", replacement: "[redacted-github-pat]" },
    { label: "gitlab_pat", pattern: "(glpat-[a-zA-Z0-9\\-]{20})", flags: "g", replacement: "[redacted-gitlab-pat]" },
    { label: "api_key", pattern: "(api[_-]?key\\s*[=:]\\s*)([^\\s,;]+)", flags: "i", replacement: "$1[redacted]" },
    { label: "bearer", pattern: "(authorization\\s*:\\s*bearer\\s+)([^\\s]+)", flags: "i", replacement: "$1[redacted]" },
    { label: "secret", pattern: "((?:secret|token|password)\\s*[=:]\\s*)([^\\s,;]+)", flags: "i", replacement: "$1[redacted]" },
  ],
  suppression: {},
  enrichment: {
    include_structured_summary: true,
    include_by_category: [],
    detect_complexity: true,
    detect_leetcode_patterns: true,
    detect_anti_patterns: true,
  },
  examination: {
    sequential_plan_prompt: true,
    auto_examine_on_edit: true,
    auto_examine_on_test_failure: true,
    leverage_engineering_baseline: true,
  },
  manifest: DEFAULT_MANIFEST_CONFIG,
}

const LEETCODE_PATTERNS: Record<string, RegExp> = {
  "in-place-partition": /partition|swap|dutch.?flag/i,
  "xor-cancellation": /xor|\^=|single.?number/i,
  "prefix-sum-hashmap": /prefix.?sum|cumulative.?sum/i,
  "monotonic-queue": /monotonic|deque|sliding.?window/i,
  "lru-cache": /lru|cache.*evict|ordereddict/i,
  "complexity-upgrade": /O\(n\^2\).*O\(n\s*log\s*n\)|O\(n\^2\).*O\(n\)/i,
}

async function loadConfig(directory: string): Promise<OutputFilterConfig> {
  const file = Bun.file(`${directory}/.opencode/output-filter.config.json`)

  if (!(await file.exists())) {
    return DEFAULT_CONFIG
  }

  try {
    const parsed = (await file.json()) as Partial<OutputFilterConfig>
    return {
      enabled: parsed.enabled ?? DEFAULT_CONFIG.enabled,
      max_output_chars:
        parsed.max_output_chars ?? DEFAULT_CONFIG.max_output_chars,
      redaction_patterns:
        parsed.redaction_patterns ?? DEFAULT_CONFIG.redaction_patterns,
      suppression: parsed.suppression ?? DEFAULT_CONFIG.suppression,
      enrichment: {
        ...DEFAULT_CONFIG.enrichment,
        ...(parsed.enrichment ?? {}),
      },
      examination: {
        ...DEFAULT_CONFIG.examination,
        ...(parsed.examination ?? {}),
      },
      manifest: {
        ...DEFAULT_CONFIG.manifest,
        ...(parsed.manifest ?? {}),
      },
    }
  } catch (err) {
    console.warn(
      `[output-filter] Falha ao carregar config (${directory}/.opencode/output-filter.config.json):`,
      err instanceof Error ? err.message : err,
      "— usando DEFAULT_CONFIG (fallback com redaction embutida)",
    )
    return DEFAULT_CONFIG
  }
}

function classifyTool(tool: string, args: Record<string, unknown>): string {
  if (tool === "read" || tool === "glob" || tool === "grep") {
    return "file_reading"
  }

  if (tool === "edit" || tool === "write") {
    return "file_modification"
  }

  if (tool === "task") {
    return "subtask_delegation"
  }

  if (tool !== "bash") {
    return "shell_command"
  }

  const command = String(args.command ?? "")

  if (/(^|\s)(pytest|py\.test|python -m pytest|make test)\b/.test(command)) {
    return "test_execution"
  }

  if (/(^|\s)(ruff|mypy|bandit|make lint|make typecheck|make security)\b/.test(command)) {
    return "code_analysis"
  }

  return "shell_command"
}

// normalizeFlags and applyRedactions are imported from ../lib/shared.ts

function matchesAny(line: string, patterns: string[]): boolean {
  return patterns.some((pattern) => {
    try {
      return new RegExp(pattern, "i").test(line)
    } catch {
      return false
    }
  })
}

function reduceNoise(text: string, rule?: SuppressionRule): string {
  if (!rule) {
    return text
  }

  const filtered = text
    .split("\n")
    .filter((line) => {
      if (matchesAny(line, rule.keep_patterns)) {
        return true
      }
      if (matchesAny(line, rule.suppress_patterns)) {
        return false
      }
      return true
    })

  if (filtered.length <= rule.max_output_lines) {
    return filtered.join("\n")
  }

  const headCount = Math.max(1, Math.floor(rule.max_output_lines * 0.35))
  const tailCount = Math.max(1, rule.max_output_lines - headCount)
  const omitted = filtered.length - headCount - tailCount

  return [
    ...filtered.slice(0, headCount),
    `[output-filter] ${omitted} linhas omitidas para reduzir ruido.`,
    ...filtered.slice(-tailCount),
  ].join("\n")
}

function truncateText(
  text: string,
  maxOutputChars: number,
): { text: string; truncated: boolean } {
  if (maxOutputChars <= 0 || text.length <= maxOutputChars) {
    return { text, truncated: false }
  }

  const suffix = "\n\n[output-filter] Saida truncada para reduzir ruido."
  const limit = Math.max(0, maxOutputChars - suffix.length)

  return {
    text: `${text.slice(0, limit)}${suffix}`,
    truncated: true,
  }
}

function detectComplexities(text: string): string[] {
  return [...new Set(text.match(/O\([^\n)]+\)/g) ?? [])]
}

function detectLeetCodePatterns(text: string): string[] {
  return Object.entries(LEETCODE_PATTERNS)
    .filter(([, pattern]) => pattern.test(text))
    .map(([name]) => name)
}

function detectAntiPatterns(text: string): string[] {
  const anti: string[] = []

  // Nested loop detection without ReDoS: count "for " occurrences
  // and check if at least two are within 300 chars of each other
  const forRegex = /\bfor\b/g
  const forPositions: number[] = []
  let match: RegExpExecArray | null
  while ((match = forRegex.exec(text)) !== null) {
    forPositions.push(match.index)
  }
  for (let i = 1; i < forPositions.length; i++) {
    if (forPositions[i] - forPositions[i - 1] <= 300) {
      anti.push("possivel_laco_aninhado")
      break
    }
  }

  if (/except\s*:/i.test(text)) {
    anti.push("bare_except")
  }
  if (/lru_cache\(\)/.test(text) && !/maxsize/.test(text)) {
    anti.push("cache_sem_limite_explicito")
  }
  return anti
}

function parseTestMetrics(text: string): Record<string, number> {
  const readMetric = (pattern: RegExp) => Number(text.match(pattern)?.[1] ?? 0)
  return {
    passed: readMetric(/(\d+) passed/),
    failed: readMetric(/(\d+) failed/),
    errors: readMetric(/(\d+) error/),
    skipped: readMetric(/(\d+) skipped/),
  }
}

function parseAnalysisMetrics(text: string): Record<string, number> {
  const lines = text.split("\n")
  return {
    error_lines: lines.filter((line) => /error/i.test(line)).length,
    warning_lines: lines.filter((line) => /warning/i.test(line)).length,
  }
}

function buildSummary(
  category: string,
  args: Record<string, unknown>,
  text: string,
  config: OutputFilterConfig,
): Record<string, unknown> {
  const summary: Record<string, unknown> = {
    categoria: category,
  }

  if (category === "test_execution") {
    summary.metricas_teste = parseTestMetrics(text)
  }

  if (category === "code_analysis") {
    summary.metricas_analise = parseAnalysisMetrics(text)
  }

  if (config.enrichment.detect_complexity) {
    const complexities = detectComplexities(text)
    if (complexities.length > 0) {
      summary.complexidade = complexities
    }
  }

  if (config.enrichment.detect_leetcode_patterns) {
    const patterns = detectLeetCodePatterns(text)
    if (patterns.length > 0) {
      summary.padroes_algoritmicos = patterns
    }
  }

  if (config.enrichment.detect_anti_patterns) {
    const antiPatterns = detectAntiPatterns(text)
    if (antiPatterns.length > 0) {
      summary.sinais_de_risco = antiPatterns
    }
  }

  if (category === "file_modification" && config.examination.auto_examine_on_edit) {
    summary.proximo_passo_recomendado =
      "Use a tool examine-algorithm para exame estruturado do trecho alterado."
  }

  if (category === "test_execution" && config.examination.auto_examine_on_test_failure) {
    const failures = parseTestMetrics(text).failed + parseTestMetrics(text).errors
    if (failures > 0) {
      summary.proximo_passo_recomendado =
        "Cruze a falha com um exame estruturado do algoritmo afetado."
    }
  }

  if (typeof args.command === "string" && args.command.trim() !== "") {
    summary.comando = sanitizeCommandValue(
      args.command,
      config.redaction_patterns,
    ).text
  }

  return summary
}

function formatStructuredPrefix(summary: Record<string, unknown>): string {
  return [
    "[output-filter] resumo estruturado",
    JSON.stringify(summary, null, 2),
    "[output-filter] saida filtrada",
  ].join("\n")
}

function parseJsonLike(text: string): unknown | null {
  const candidate = text.trim()

  // Try direct parse first
  if (candidate.startsWith("{") || candidate.startsWith("[")) {
    try {
      return JSON.parse(candidate)
    } catch {
      // Fall through to code block extraction
    }
  }

  // Extract JSON from markdown code blocks: ```json ... ``` or ``` ... ```
  const codeBlockMatch = candidate.match(/```(?:json)?\s*\n?([\s\S]*?)```/)
  if (codeBlockMatch) {
    const inner = codeBlockMatch[1].trim()
    if (inner.startsWith("{") || inner.startsWith("[")) {
      try {
        return JSON.parse(inner)
      } catch {
        return null
      }
    }
  }

  return null
}

// isSensitiveKey is imported from ../lib/shared.ts

function sanitizeCommandValue(
  value: string,
  rules: PatternRule[],
): { text: string; redacted: boolean } {
  const redacted = applyRedactions(value, rules)
  return {
    text: redacted.text,
    redacted: redacted.applied.length > 0,
  }
}

function redactJsonValue(
  value: unknown,
  rules: PatternRule[],
  parentKey?: string,
): unknown {
  if (parentKey && isSensitiveKey(parentKey)) {
    return typeof value === "string" ? "[redacted]" : value
  }

  if (typeof value === "string") {
    return applyRedactions(value, rules).text
  }

  if (Array.isArray(value)) {
    return value.map((item) => redactJsonValue(item, rules, parentKey))
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nested]) => [
        key,
        redactJsonValue(nested, rules, key),
      ]),
    )
  }

  return value
}

// --- Manifest Persistence Functions (Phase 3) ---

type PhaseLabel = "exploration" | "implementation" | "review"

// stableStringify and sortJsonValue are imported from ../lib/shared.ts

function computeStateHash(
  manifest: Omit<SessionManifest, "state_hash">,
): string {
  const canonical = stableStringify(manifest)
  const hasher = new Bun.CryptoHasher("sha256")
  hasher.update(canonical)
  return `sha256:${hasher.digest("hex")}`
}

function detectPhase(tool: string, args: Record<string, unknown>): PhaseLabel {
  if (["read", "glob", "grep", "examine-algorithm"].includes(tool)) {
    return "exploration"
  }

  if (
    tool === "task" &&
    (args.agent === "reviewer" ||
      String(args.description ?? "").includes("review"))
  ) {
    return "review"
  }

  if (["write", "edit", "bash"].includes(tool)) {
    return "implementation"
  }

  return "implementation"
}

function createEmptyManifest(
  sessionID: string,
  directory: string,
  agent: string,
): SessionManifest {
  const now = new Date().toISOString()
  const base: Omit<SessionManifest, "state_hash"> = {
    session_id: sessionID,
    agent,
    timestamp: now,
    directory,
    phases: {
      exploration: { status: "pending", agent: "explore" },
      implementation: { status: "pending", agent: "general" },
      review: { status: "pending", agent: "reviewer" },
    },
    resume_capable: false,
    total_tokens: 0,
    total_cost: 0,
    message_count: 0,
    last_tool_call: "",
    created_at: now,
    updated_at: now,
  }

  const state_hash = computeStateHash(base)
  return { ...base, state_hash }
}

function sanitizeFileComponent(value: string): string {
  const sanitized = value.replace(/[^a-zA-Z0-9._-]+/g, "-")
  return sanitized.length > 0 ? sanitized : "unknown-session"
}

function getManifestFilename(manifest: SessionManifest): string {
  return `${sanitizeFileComponent(manifest.session_id)}.json`
}

function getSessionID(input: unknown): string {
  if (!input || typeof input !== "object") {
    return "unknown-session"
  }

  const record = input as Record<string, unknown>
  const sessionID = record.sessionID ?? record.sessionId ?? record.session_id
  return typeof sessionID === "string" && sessionID.length > 0
    ? sessionID
    : "unknown-session"
}

function getInputAgent(input: unknown): string {
  if (!input || typeof input !== "object") {
    return "unknown"
  }

  const record = input as Record<string, unknown>
  const agent = record.agent ?? record.agentName
  return typeof agent === "string" && agent.length > 0 ? agent : "unknown"
}

function markPhaseComplete(phase: ManifestPhase, timestamp: number): void {
  if (phase.status === "complete") {
    return
  }

  if (!phase.started_at) {
    phase.started_at = timestamp
  }

  phase.status = "complete"
  phase.completed_at = timestamp
}

async function persistManifest(
  manifest: SessionManifest,
  directory: string,
  config: ManifestConfig,
): Promise<void> {
  if (!config.enabled) {
    return
  }

  const manifestDir = path.resolve(directory, config.persist_dir)

  try {
    await mkdir(manifestDir, { recursive: true })
    await writeFile(path.join(manifestDir, ".keep"), "", { flag: "a" })
  } catch {
    // Silencioso: falha ao criar diretório de manifest não deve poluir TUI
    return
  }

  const filename = getManifestFilename(manifest)
  const finalPath = path.join(manifestDir, filename)
  const tempPath = `${finalPath}.tmp`
  const content = JSON.stringify(manifest, null, 2)

  try {
    if (config.atomic_write) {
      await writeFile(tempPath, content)
      try {
        await rename(tempPath, finalPath)
      } catch (renameErr) {
        // Rename failed — attempt cleanup of orphaned temp file
        try {
          await unlink(tempPath)
        } catch {
          // Best-effort cleanup.
        }
        throw renameErr
      }
    } else {
      await writeFile(finalPath, content)
    }

    try {
      await writeFile(path.join(manifestDir, "latest.json"), content)
    } catch {
      // Silencioso: latest.json é best-effort
    }
  } catch {
    // Silencioso: falha de persistência não deve poluir TUI
  }
}

async function rotateManifests(
  directory: string,
  config: ManifestConfig,
): Promise<void> {
  if (config.max_manifests <= 0) {
    return
  }

  const manifestDir = path.resolve(directory, config.persist_dir)

  try {
    const entries: Array<{ path: string; mtime: number }> = []
    for (const entry of await readdir(manifestDir)) {
      if (
        entry.endsWith("latest.json") ||
        entry.endsWith(".keep") ||
        !entry.endsWith(".json")
      ) {
        continue
      }
      const fullPath = path.join(manifestDir, entry)
      try {
        const fileStat = await stat(fullPath)
        entries.push({ path: fullPath, mtime: fileStat.mtimeMs })
      } catch {
        entries.push({ path: fullPath, mtime: 0 })
      }
    }

    entries.sort((a, b) => a.mtime - b.mtime)
    const sorted = entries.map((e) => e.path)

    if (sorted.length <= config.max_manifests) {
      return
    }

    const toDelete = sorted.slice(0, sorted.length - config.max_manifests)
    for (const filePath of toDelete) {
      try {
        await unlink(filePath)
      } catch {
        // Silencioso: falha ao remover manifest antigo
      }
    }
  } catch {
    // Silencioso: falha ao rotacionar manifests
  }
}

const OutputFilterPlugin: Plugin = async ({ directory }) => {
  const config = await loadConfig(directory)

  // Manifest state: one manifest per session, keyed by sessionID
  const manifestStates = new Map<string, SessionManifest>()

  function getOrCreateManifest(
    sessionID: string,
    agent: string,
  ): SessionManifest {
    let manifest = manifestStates.get(sessionID)
    if (!manifest) {
      manifest = createEmptyManifest(sessionID, directory, agent)
      manifestStates.set(sessionID, manifest)
    }
    return manifest
  }

  function updateManifestPhase(
    manifest: SessionManifest,
    phase: PhaseLabel,
  ): void {
    const now = Date.now()
    const currentPhase = manifest.phases[phase]

    if (currentPhase.status === "pending") {
      currentPhase.status = "in_progress"
      currentPhase.started_at = now
    }

    if (phase === "implementation") {
      markPhaseComplete(manifest.phases.exploration, now)
    }

    if (phase === "review") {
      markPhaseComplete(manifest.phases.exploration, now)
      markPhaseComplete(manifest.phases.implementation, now)
    }

    manifest.updated_at = new Date(now).toISOString()
    manifest.resume_capable = true
  }

  function updateManifestTokens(
    manifest: SessionManifest,
    metadata: { total_tokens?: number; total_cost?: number },
  ): void {
    if (metadata.total_tokens) {
      manifest.total_tokens = Math.max(
        manifest.total_tokens,
        metadata.total_tokens,
      )
    }
    if (metadata.total_cost) {
      manifest.total_cost = Math.max(
        manifest.total_cost,
        metadata.total_cost,
      )
    }
  }

  async function trackAndPersistManifest(
    sessionID: string,
    tool: string,
    args: Record<string, unknown>,
    agent: string,
    metadata?: { total_tokens?: number; total_cost?: number },
  ): Promise<void> {
    if (!config.manifest.enabled) {
      return
    }

    const manifest = getOrCreateManifest(sessionID, agent)
    const phase = config.manifest.auto_phase_tracking
      ? detectPhase(tool, args)
      : "implementation"

    // Update phase tracking
    updateManifestPhase(manifest, phase)

    // Track last tool call
    manifest.last_tool_call = tool
    manifest.message_count += 1
    updateManifestTokens(manifest, metadata ?? {})

    // Recompute state_hash
    const { state_hash: _, ...rest } = manifest
    if (config.manifest.state_hash_enabled) {
      manifest.state_hash = computeStateHash(rest)
    }

    // Fire-and-forget persistence (não bloqueia output do hook)
    persistManifest(manifest, directory, config.manifest).catch(() => {
      // Silencioso
    })
    rotateManifests(directory, config.manifest).catch(() => {
      // Silencioso
    })
  }

  return {
    "experimental.chat.system.transform": async (_input, output) => {
      if (!config.examination.sequential_plan_prompt) {
        return
      }

      output.system.push(
        [
          "Para tarefas com algoritmos, saidas estruturadas ou exame tecnico,",
          "use raciocinio sequencial planejado:",
          "1) objetivo, 2) estrategia, 3) complexidade/memoria,",
          "4) casos limite, 5) validacao e riscos.",
          "Quando precisar de um parecer heuristico estruturado,",
          "prefira a tool local `examine-algorithm`.",
        ].join(" "),
      )
    },
    "tool.execute.after": async (input, output) => {
      const filterStartTime = performance.now()

      // Record command latency from metadata if available
      if (output.metadata && typeof (output.metadata as Record<string, unknown>).duration_ms === "number") {
        metrics.recordCommandLatency(
          input.tool,
          (output.metadata as Record<string, unknown>).duration_ms as number,
        )
      }

      // Track path traversal attempts
      if (input.tool === "examine-algorithm" && output.output && typeof output.output === "string") {
        if (output.output.includes("worktree atual") || output.output.includes("nao e permitida")) {
          metrics.incrementPathTraversalAttempts()
        }
      }

      if (!config.enabled || typeof output.output !== "string") {
        return
      }

      if (config.manifest.enabled) {
        trackAndPersistManifest(
          getSessionID(input),
          input.tool,
          (input.args ?? {}) as Record<string, unknown>,
          getInputAgent(input),
          output.metadata as { total_tokens?: number; total_cost?: number } | undefined,
        ).catch(() => {
          // Silencioso: erros de manifest não devem poluir stderr do TUI
        })
      }

      const category = classifyTool(input.tool, input.args ?? {})
      const rawJson = parseJsonLike(output.output)
      const redactedJson = rawJson === null
        ? null
        : redactJsonValue(rawJson, config.redaction_patterns)
      const jsonText = redactedJson === null
        ? null
        : JSON.stringify(redactedJson, null, 2)
      const summarySource = rawJson === null ? output.output : (jsonText ?? output.output)
      const summary = buildSummary(
        category,
        (input.args ?? {}) as Record<string, unknown>,
        summarySource,
        config,
      )

      if (rawJson !== null) {
        const boundedJson = truncateText(
          jsonText ?? JSON.stringify(rawJson, null, 2),
          config.max_output_chars,
        )

        // Record JSON preservation metric
        metrics.recordJsonPreservation(true)
        const wasRedacted = jsonText !== null && jsonText !== JSON.stringify(rawJson, null, 2)
        metrics.recordSecretRedaction(wasRedacted ? 1 : 0)
        metrics.recordFilterProcessingTime(performance.now() - filterStartTime)

        output.output = boundedJson.truncated
          ? JSON.stringify(
              {
                _output_filter: {
                  preservedStructuredOutput: true,
                  truncated: true,
                  note:
                    "JSON estruturado excedeu o limite; consulte metadata.outputFilter.structuredSummary.",
                },
              },
              null,
              2,
            )
          : boundedJson.text
        output.metadata = {
          ...(output.metadata ?? {}),
          outputFilter: {
            category,
            preservedStructuredOutput: true,
            redactions:
              jsonText !== null && jsonText !== JSON.stringify(rawJson, null, 2)
                ? ["json_value_redaction"]
                : [],
            truncated: boundedJson.truncated,
            structuredSummary: summary,
          },
        }

        if (boundedJson.truncated) {
          output.title = `${output.title} [filtrado]`
        }
        return
      }

      const reduced = reduceNoise(
        output.output,
        config.suppression[category],
      )
      const redacted = applyRedactions(reduced, config.redaction_patterns)
      const truncated = truncateText(redacted.text, config.max_output_chars)
      const shouldIncludePrefix =
        config.enrichment.include_structured_summary &&
        (!_isInteractive ||
          config.enrichment.include_by_category.includes(category))
      const combinedOutput = shouldIncludePrefix
        ? `${formatStructuredPrefix(summary)}\n${truncated.text}`
        : truncated.text
      const finalOutput = truncateText(
        combinedOutput,
        config.max_output_chars,
      )

      output.output = finalOutput.text
      output.metadata = {
        ...(output.metadata ?? {}),
        outputFilter: {
          category,
          preservedStructuredOutput: false,
          redactions: redacted.applied,
          truncated: truncated.truncated || finalOutput.truncated,
          structuredSummary: summary,
        },
      }

      if (
        redacted.applied.length > 0 ||
        truncated.truncated ||
        finalOutput.truncated
      ) {
        output.title = `${output.title} [filtrado]`
      }

      // Record metrics for non-JSON path
      metrics.recordJsonPreservation(false)
      metrics.recordSecretRedaction(redacted.applied.length)
      metrics.recordFilterProcessingTime(performance.now() - filterStartTime)
    },
  }
}

export default OutputFilterPlugin
