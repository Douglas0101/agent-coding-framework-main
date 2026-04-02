/**
 * Shared pure functions for OpenCode plugins, tools, and tests.
 *
 * Extracted to prevent code drift between source and test implementations.
 * V-11: Duplicated functions consolidated into single source of truth.
 */
import path from "node:path"

// === Types ===

export type PatternRule = {
  label: string
  pattern: string
  flags?: string
  replacement: string
}

export type CodeEntity = {
  name: string
  line_start: number
  line_end: number
}

export type Signal = {
  label: string
  detail: string
  matched: boolean
}

// === Redaction (from output-filter.ts) ===

export function normalizeFlags(flags?: string): string {
  return Array.from(new Set(`${flags ?? ""}g`.split(""))).join("")
}

export function applyRedactions(
  text: string,
  rules: PatternRule[],
): { text: string; applied: string[] } {
  let next = text
  const applied = new Set<string>()

  for (const rule of rules) {
    try {
      const regex = new RegExp(rule.pattern, normalizeFlags(rule.flags))
      const replaced = next.replace(regex, rule.replacement)
      if (replaced !== next) {
        next = replaced
        applied.add(rule.label)
      }
    } catch {
      continue
    }
  }

  return { text: next, applied: [...applied] }
}

export function isSensitiveKey(key: string): boolean {
  return /(api[_-]?key|authorization|token|password|secret|private[_-]?key|credential|connection[_-]?string|access[_-]?key)/i.test(key)
}

// === String helpers (from examine-algorithm.ts) ===

export function includesAny(text: string, values: string[]): boolean {
  return values.some((value) => text.includes(value))
}

// === Entity extraction (from examine-algorithm.ts) ===

export function extractPythonEntities(text: string, prefix: "def" | "class"): CodeEntity[] {
  const lines = text.split("\n")
  const result: CodeEntity[] = []

  for (let index = 0; index < lines.length; index += 1) {
    const regex =
      prefix === "def"
        ? /^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/
        : /^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(|:)/
    const match = lines[index].match(regex)
    if (!match) continue
    let lineEnd = index + 1
    const baseIndent = lines[index].match(/^(\s*)/)?.[1].length ?? 0
    for (let probe = index + 1; probe < lines.length; probe += 1) {
      if (lines[probe].trim() === "") continue
      const currentIndent = lines[probe].match(/^(\s*)/)?.[1].length ?? 0
      if (currentIndent <= baseIndent) break
      lineEnd = probe + 1
    }
    result.push({ name: match[1], line_start: index + 1, line_end: lineEnd })
  }
  return result
}

export function detectLanguage(filePath: string | null, text: string): string {
  const normalized = filePath?.toLowerCase() ?? ""
  if (normalized.endsWith(".py")) return "python"
  if (normalized.endsWith(".ts") || normalized.endsWith(".tsx")) return "typescript"
  if (normalized.endsWith(".rs")) return "rust"
  if (/^def |^class /m.test(text)) return "python"
  if (/^function |^const |^export /m.test(text)) return "typescript"
  if (/^fn |^struct |^impl |^mod /m.test(text)) return "rust"
  return "unknown"
}

export function collectSignals(text: string): Signal[] {
  return [
    { label: "iteracao", detail: "Detecta indicios de lacos ou varreduras sequenciais.", matched: includesAny(text, ["for ", "while ", ".map(", ".filter("]) },
    { label: "recursao", detail: "Detecta indicios simples de chamadas recursivas.", matched: includesAny(text, ["recurs", "dfs(", "backtrack("]) },
    { label: "ordenacao", detail: "Detecta ordenacao ou comparacao dominante.", matched: includesAny(text, ["sort(", "sorted(", "compare", "order"]) },
    { label: "hashing", detail: "Detecta uso provavel de mapa, set ou dicionario.", matched: includesAny(text, ["dict", "map", "set", "hash"]) },
    { label: "programacao_dinamica", detail: "Detecta termos tipicos de memoizacao ou tabela DP.", matched: includesAny(text, ["memo", "cache", " dp", "table"]) },
    { label: "bitwise", detail: "Detecta operacoes bit a bit relevantes para custo ou risco.", matched: includesAny(text, ["<<", ">>", "&", "|", "^", "bit_count"]) },
  ]
}

// === Path security (from examine-algorithm.ts) ===

const BLOCKED_PATH_PATTERNS = [
  /(^|\/)\.\.($|\/)/,
  /\.env(?!\.example)/i,
  /\.pem$/i,
  /\.key$/i,
  /\.p12$/i,
  /\.pfx$/i,
  /^id_(rsa|dsa|ecdsa|ed25519)/i,
  /\.npmrc$/i,
  /\.dockercfg$/i,
  /credentials\.json$/i,
  /secrets\.json$/i,
  /service[_-]?account.*\.json$/i,
  /^\.aws\//i,
  /^\.gcloud\//i,
  /token\.json$/i,
]

export function isBlockedSensitivePath(targetPath: string): boolean {
  const normalized = targetPath.replace(/\\/g, "/")
  let decoded = normalized
  try {
    decoded = decodeURIComponent(normalized)
  } catch {
    decoded = normalized
  }

  const candidates = [normalized, decoded, path.basename(normalized), path.basename(decoded)]
  return BLOCKED_PATH_PATTERNS.some((pattern) => candidates.some((value) => pattern.test(value)))
}

// === Manifest helpers (from output-filter.ts) ===

export function sortJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortJsonValue)
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, sortJsonValue(nested)]),
    )
  }

  return value
}

export function stableStringify(value: unknown): string {
  return JSON.stringify(sortJsonValue(value))
}
