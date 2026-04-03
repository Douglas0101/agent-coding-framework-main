import { readFile, realpath } from "node:fs/promises"
import path from "node:path"

import { tool } from "@opencode-ai/plugin"

import {
  type CodeEntity,
  type Signal,
  includesAny,
  extractPythonEntities,
  detectLanguage,
  collectSignals,
  isBlockedSensitivePath,
} from "../lib/shared"

import { analysisCache, AnalysisCache } from "../lib/cache"
import { getParser, resolveTsVariant, type TreeSitterParser } from "../lib/tree-sitter-parsers"

const MAX_INLINE_CODE_SIZE = 50_000 // 50KB limit for inline code analysis

const PATTERN_CATALOG: Record<string, { regex: RegExp; lc: string }> = {
  "in-place-partition": { regex: /partition|swap|dutch.?flag/i, lc: "LC 75" },
  "xor-cancellation": { regex: /xor|\^=|single.?number/i, lc: "LC 136" },
  "prefix-sum-hashmap": { regex: /prefix.?sum|cumulative.?sum/i, lc: "LC 560" },
  "monotonic-queue": { regex: /monotonic|deque|sliding.?window/i, lc: "LC 239" },
  "lru-cache": { regex: /lru|ordereddict|cache.*evict/i, lc: "LC 146" },
}

// extractPythonEntities, detectLanguage, collectSignals, includesAny
// são importados de ../lib/shared.ts (ver imports acima).

// === Tree-sitter entity extraction (primary) ===

function entitiesFromTreeSitter(
  parser: TreeSitterParser,
  code: string,
  nodeTypes: string[],
  nameField: string | null,
): CodeEntity[] {
  const tree = parser.parse(code)
  if (!tree) return []

  const entities: CodeEntity[] = []
  const cursor = tree.walk()

  function visit(): boolean {
    const node = cursor.currentNode
    if (nodeTypes.includes(node.type)) {
      let name = "anonymous"
      if (nameField) {
        const nameNode = node.childForFieldName(nameField)
        if (nameNode) name = nameNode.text
      } else {
        // Fallback: first identifier child
        for (let i = 0; i < node.childCount; i++) {
          const child = node.child(i)
          if (child && child.type === "identifier") {
            name = child.text
            break
          }
        }
      }
      entities.push({
        name,
        line_start: node.startPosition.row + 1,
        line_end: node.endPosition.row + 1,
      })
    }

    if (cursor.gotoFirstChild()) {
      do { visit() } while (cursor.gotoNextSibling())
      cursor.gotoParent()
    }
    return true
  }

  visit()
  tree.delete()
  return entities
}

async function extractTypeScriptEntitiesTreeSitter(
  text: string,
  kind: "function" | "class" | "interface" | "type" | "enum",
  filePath: string | null,
): Promise<CodeEntity[]> {
  const variant = resolveTsVariant(filePath)
  const parser = await getParser(variant)
  if (!parser) return []

  const config: Record<string, { types: string[]; nameField: string }> = {
    function: { types: ["function_declaration", "method_definition"], nameField: "name" },
    class: { types: ["class_declaration"], nameField: "name" },
    interface: { types: ["interface_declaration"], nameField: "name" },
    type: { types: ["type_alias_declaration"], nameField: "name" },
    enum: { types: ["enum_declaration"], nameField: "name" },
  }

  const { types, nameField } = config[kind] ?? config.function

  // Extract from AST
  const entities = entitiesFromTreeSitter(parser, text, types, nameField)

  // Also capture arrow functions assigned to const (not caught by function_declaration)
  if (kind === "function") {
    const tree = parser.parse(text)
    if (tree) {
      const cursor = tree.walk()
      const visitArrow = () => {
        const node = cursor.currentNode
        if (node.type === "variable_declarator") {
          const value = node.childForFieldName("value")
          if (value && value.type === "arrow_function") {
            const nameNode = node.childForFieldName("name")
            if (nameNode) {
              entities.push({
                name: nameNode.text,
                line_start: node.startPosition.row + 1,
                line_end: node.endPosition.row + 1,
              })
            }
          }
        }
        if (cursor.gotoFirstChild()) {
          do { visitArrow() } while (cursor.gotoNextSibling())
          cursor.gotoParent()
        }
      }
      visitArrow()
      tree.delete()
    }
  }

  return entities
}

async function extractRustEntitiesTreeSitter(
  text: string,
  kind: "fn" | "struct" | "impl" | "mod" | "trait" | "enum",
): Promise<CodeEntity[]> {
  const parser = await getParser("rust")
  if (!parser) return []

  const config: Record<string, { types: string[]; nameField: string | null }> = {
    fn: { types: ["function_item"], nameField: "name" },
    struct: { types: ["struct_item"], nameField: "name" },
    impl: { types: ["impl_item"], nameField: null }, // impl has no single "name" field
    mod: { types: ["mod_item"], nameField: "name" },
    trait: { types: ["trait_item"], nameField: "name" },
    enum: { types: ["enum_item"], nameField: "name" },
  }

  const { types, nameField } = config[kind] ?? config.fn
  return entitiesFromTreeSitter(parser, text, types, nameField)
}

// === Regex entity extraction (fallback) ===
/**
 * Finds the end line of a brace-delimited scope (functions, classes, blocks).
 * Uses brace depth counting to handle nested braces correctly.
 */
function findBraceScopeEnd(lines: string[], startIndex: number): number {
  let braceDepth = 0
  let inString = false
  let stringChar = ""
  let lineEnd = startIndex + 1

  // Find opening brace on start line
  for (const char of lines[startIndex]) {
    if (char === '"' || char === "'") {
      if (!inString) {
        inString = true
        stringChar = char
      } else if (char === stringChar) {
        inString = false
      }
    } else if (!inString) {
      if (char === "{") {
        braceDepth++
      } else if (char === "}") {
        braceDepth--
      }
    }
  }

  // If no opening brace found, assume single-line
  if (braceDepth === 0) {
    return startIndex + 1
  }

  // Scan subsequent lines
  for (let i = startIndex + 1; i < lines.length; i++) {
    for (const char of lines[i]) {
      if (char === '"' || char === "'") {
        if (!inString) {
          inString = true
          stringChar = char
        } else if (char === stringChar) {
          inString = false
        }
      } else if (!inString) {
        if (char === "{") {
          braceDepth++
        } else if (char === "}") {
          braceDepth--
        }
      }
    }
    lineEnd = i + 1
    if (braceDepth === 0) {
      break
    }
  }

  return lineEnd
}

/**
 * Extracts TypeScript/JavaScript entities (functions, classes, arrow functions).
 * Uses brace-delimited scope detection.
 */
function extractTypeScriptEntities(
  text: string,
  kind: "function" | "class" | "interface" | "type" | "enum",
): CodeEntity[] {
  const lines = text.split("\n")
  const result: CodeEntity[] = []

  const patterns: RegExp[] =
    kind === "function"
      ? [
          /^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(/,
          /^\s*(?:export\s+)?const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_$][a-zA-Z0-9_$]*)\s*=>/,
          /^\s*(?:export\s+)?(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{/,
        ]
      : kind === "class"
        ? [
            /^\s*(?:export\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:extends|implements)?/,
          ]
        : kind === "interface"
          ? [
              /^\s*(?:export\s+)?interface\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[{(<]/,
            ]
          : kind === "type"
            ? [
                /^\s*(?:export\s+)?type\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=/,
              ]
            : [
                /^\s*(?:export\s+)?enum\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[{(]/,
              ]

  for (let index = 0; index < lines.length; index++) {
    let matchedName: string | null = null

    for (const pattern of patterns) {
      const match = lines[index].match(pattern)
      if (match) {
        matchedName = match[1]
        break
      }
    }

    if (!matchedName) {
      continue
    }

    const lineEnd = findBraceScopeEnd(lines, index)

    result.push({
      name: matchedName,
      line_start: index + 1,
      line_end: lineEnd,
    })
  }

  return result
}

/**
 * Extracts Rust entities (functions, structs, impl blocks, modules).
 * Uses brace-delimited scope detection.
 */
function extractRustEntities(
  text: string,
  kind: "fn" | "struct" | "impl" | "mod" | "trait" | "enum",
): CodeEntity[] {
  const lines = text.split("\n")
  const result: CodeEntity[] = []

  const patterns: { regex: RegExp; nameGroup: number }[] =
    kind === "fn"
      ? [{ regex: /^\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[<(]/, nameGroup: 1 }]
      : kind === "struct"
        ? [{ regex: /^\s*(?:pub\s+)?struct\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(|\{|$)/, nameGroup: 1 }]
        : kind === "impl"
          ? [{ regex: /^\s*(?:pub\s+)?impl(?:<[^>]+>)?\s+(?:[a-zA-Z_][a-zA-Z0-9_]*\s+for\s+)?([a-zA-Z_][a-zA-Z0-9_]*)/, nameGroup: 1 }]
          : kind === "mod"
            ? [{ regex: /^\s*(?:pub\s+)?mod\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[;{]/, nameGroup: 1 }]
            : kind === "trait"
              ? [{ regex: /^\s*(?:pub\s+)?trait\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\{|<|$)/, nameGroup: 1 }]
              : [{ regex: /^\s*(?:pub\s+)?enum\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\{|<|$)/, nameGroup: 1 }]

  for (let index = 0; index < lines.length; index++) {
    let matchedName: string | null = null

    for (const { regex, nameGroup } of patterns) {
      const match = lines[index].match(regex)
      if (match) {
        matchedName = match[nameGroup]
        break
      }
    }

    if (!matchedName) {
      continue
    }

    const lineEnd = findBraceScopeEnd(lines, index)

    result.push({
      name: matchedName,
      line_start: index + 1,
      line_end: lineEnd,
    })
  }

  return result
}

function estimateComplexity(text: string, signals: Signal[]): { time: string; space: string; confidence: string } {
  const loops = (text.match(/for |while |\.map\(|\.filter\(/g) ?? []).length
  const active = new Set(signals.filter((item) => item.matched).map((item) => item.label))

  if (active.has("ordenacao")) {
    return { time: "O(n log n) provável", space: "O(1) a O(n)", confidence: "media" }
  }
  if (active.has("programacao_dinamica")) {
    return { time: "O(n) a O(n^2) provável", space: "O(n) provável", confidence: "media" }
  }
  if (loops >= 2) {
    return { time: "O(n^2) heurístico", space: "O(1) a O(n)", confidence: "media" }
  }
  if (loops === 1 || active.has("hashing")) {
    return { time: "O(n) provável", space: active.has("hashing") ? "O(n) provável" : "O(1) a O(n)", confidence: "alta" }
  }
  return { time: "Inconclusivo", space: "Inconclusivo", confidence: "baixa" }
}

function detectPatterns(text: string): Array<{ pattern: string; lc_reference: string }> {
  return Object.entries(PATTERN_CATALOG)
    .filter(([, entry]) => entry.regex.test(text))
    .map(([pattern, entry]) => ({ pattern, lc_reference: entry.lc }))
}

function buildQualitySignals(text: string, signals: Signal[], language: string = "python") {
  const antiPatterns: string[] = []
  if (/except\s*:/i.test(text)) {
    antiPatterns.push("bare_except")
  }
  if (/lru_cache\(\s*maxsize\s*=\s*none\s*\)/i.test(text)) {
    antiPatterns.push("cache_sem_limite")
  }
  if (/for[\s\S]{0,250}for /i.test(text)) {
    antiPatterns.push("possivel_laco_aninhado")
  }

  // TypeScript/JavaScript specific patterns
  if (language === "typescript") {
    if (/catch\s*\(\s*\)/i.test(text)) {
      antiPatterns.push("catch_vazio")
    }
    if (/any\b/.test(text)) {
      antiPatterns.push("tipo_any")
    }
  }

  // Rust specific patterns
  if (language === "rust") {
    if (/panic!\s*\(\s*\)/i.test(text)) {
      antiPatterns.push("panic_sem_mensagem")
    }
    if (/\.unwrap\(\)/.test(text)) {
      antiPatterns.push("unwrap_sem_tratamento")
    }
    if (/unsafe\s*\{/.test(text)) {
      antiPatterns.push("bloco_unsafe")
    }
  }

  return {
    has_docstring: /"""[\s\S]*?"""|'''[\s\S]*?'''|\/\*[\s\S]*?\*\/|\/\/[\s\S]*?$/.test(text),
    has_type_hints: /->\s*[A-Za-z_\[]|:\s*[A-Za-z_\[]|:\s*[A-Z]/.test(text),
    has_edge_case_handling: /if\s+not |if\s+.*==\s*0|raise\s+ValueError|panic!|Result::Err/.test(text),
    uses_bitwise: signals.some((signal) => signal.label === "bitwise" && signal.matched),
    anti_patterns: antiPatterns,
  }
}

function buildRecommendations(signals: Signal[], qualitySignals: ReturnType<typeof buildQualitySignals>): string[] {
  const recommendations = [
    "Confirme a analise com leitura humana e testes focados.",
    "Documente a complexidade escolhida se o trecho estiver em caminho quente.",
  ]

  if (signals.some((signal) => signal.label === "ordenacao" && signal.matched)) {
    recommendations.push("Verifique se a ordenacao pode ser evitada ou deslocada para pre-processamento.")
  }
  if (signals.some((signal) => signal.label === "hashing" && signal.matched)) {
    recommendations.push("Cheque o trade-off de memoria das estruturas auxiliares.")
  }
  if (qualitySignals.uses_bitwise) {
    recommendations.push("Garanta testes de borda explicitos para expressoes bitwise.")
  }

  return recommendations
}

async function readSource(
  filePath: string | undefined,
  inlineCode: string | undefined,
  directory: string,
  worktree: string,
): Promise<{ code: string; resolvedPath: string | null }> {
  if (inlineCode && inlineCode.trim() !== "") {
    if (inlineCode.length > MAX_INLINE_CODE_SIZE) {
      throw new Error(
        `Codigo inline excede limite de ${MAX_INLINE_CODE_SIZE} caracteres (${inlineCode.length}). ` +
        `Use file_path para analisar arquivos grandes.`
      )
    }
    return { code: inlineCode, resolvedPath: null }
  }

  if (!filePath || filePath.trim() === "") {
    throw new Error("Informe `file_path` ou `code`.")
  }

  if (isBlockedSensitivePath(filePath)) {
    throw new Error("Leitura de arquivo sensivel nao e permitida por esta tool.")
  }

  const resolvedPath = path.isAbsolute(filePath)
    ? filePath
    : path.resolve(directory, filePath)
  const canonicalWorktree = await realpath(worktree)
  const canonicalTarget = await realpath(resolvedPath)
  const relativeToWorktree = path.relative(canonicalWorktree, canonicalTarget)

  if (
    relativeToWorktree.startsWith("..") ||
    path.isAbsolute(relativeToWorktree)
  ) {
    throw new Error("A leitura deve permanecer dentro do worktree atual.")
  }

  if (isBlockedSensitivePath(canonicalTarget)) {
    throw new Error("Leitura de .env real nao e permitida por esta tool.")
  }

  const code = await readFile(canonicalTarget, "utf-8")
  return { code, resolvedPath: canonicalTarget }
}

function filterEntitiesByTarget(
  entities: CodeEntity[],
  targetName: string | undefined,
): CodeEntity[] {
  if (!targetName) {
    return entities
  }

  return entities.filter((entity) => entity.name === targetName)
}

function selectAnalysisSource(
  code: string,
  functions: CodeEntity[],
  classes: CodeEntity[],
  scope: "function" | "class" | "module" | "full",
): string {
  const lines = code.split("\n")

  if (scope === "function" && functions.length > 0) {
    return lines
      .slice(functions[0].line_start - 1, functions[0].line_end)
      .join("\n")
  }

  if (scope === "class" && classes.length > 0) {
    return lines
      .slice(classes[0].line_start - 1, classes[0].line_end)
      .join("\n")
  }

  return code
}

function validateTargetScope(
  scope: "function" | "class" | "module" | "full",
  targetName: string | undefined,
  functions: CodeEntity[],
  classes: CodeEntity[],
): string | null {
  if (scope === "function") {
    if (!targetName) {
      return "Informe `target_name` ao usar `algorithm_scope=function`."
    }
    if (functions.length === 0) {
      return `Funcao alvo nao encontrada: ${targetName}.`
    }
  }

  if (scope === "class") {
    if (!targetName) {
      return "Informe `target_name` ao usar `algorithm_scope=class`."
    }
    if (classes.length === 0) {
      return `Classe alvo nao encontrada: ${targetName}.`
    }
  }

  return null
}

export default tool({
  description:
    "Examina um algoritmo ou trecho local e retorna um parecer estruturado em JSON.",
  args: {
    file_path: tool.schema
      .string()
      .optional()
      .describe("Caminho do arquivo a ser examinado, relativo ao diretorio do projeto."),
    code: tool.schema
      .string()
      .optional()
      .describe("Trecho inline para exame quando nao houver arquivo local."),
    algorithm_scope: tool.schema
      .enum(["function", "class", "module", "full"])
      .default("full")
      .describe("Escopo pretendido da analise heuristica."),
    target_name: tool.schema
      .string()
      .optional()
      .describe("Nome da funcao ou classe de interesse, quando aplicavel."),
    include_complexity: tool.schema
      .boolean()
      .default(true)
      .describe("Inclui estimativa heuristica de complexidade."),
    include_tests: tool.schema
      .boolean()
      .default(true)
      .describe("Tenta apontar cobertura associada por convencao de caminho."),
    include_patterns: tool.schema
      .boolean()
      .default(true)
      .describe("Detecta padroes algoritmicos inspirados em LeetCode."),
  },
  async execute(args, context) {
    let code: string
    let resolvedPath: string | null

    try {
      const source = await readSource(
        args.file_path,
        args.code,
        context.directory,
        context.worktree,
      )
      code = source.code
      resolvedPath = source.resolvedPath
    } catch (error) {
      return JSON.stringify(
        {
          meta: {
            tool: "examine-algorithm",
            heuristic: true,
            agent: context.agent,
          },
          error: error instanceof Error ? error.message : "Falha ao ler fonte.",
        },
        null,
        2,
      )
    }

    const codeHash = (() => {
      try {
        const h = new (globalThis as any).Bun.CryptoHasher("sha256")
        h.update(code)
        return h.digest("hex").slice(0, 16)
      } catch {
        return `fallback-${code.length}`
      }
    })()
    const cacheKey = AnalysisCache.makeKey({
      file_path: resolvedPath ?? args.file_path ?? "",
      code_hash: codeHash,
      scope: args.algorithm_scope,
      target: args.target_name ?? "",
    })
    const cached = analysisCache.get(cacheKey)
    if (cached) {
      return JSON.stringify(cached, null, 2)
    }

    const sourceLower = code.toLowerCase()
    const language = detectLanguage(resolvedPath, sourceLower)

    // Extract entities: tree-sitter primary, regex fallback
    let parsingMethod: "tree-sitter" | "heuristic" = "heuristic"
    let extractedFunctions: CodeEntity[] = []
    let extractedClasses: CodeEntity[] = []

    if (language === "python") {
      extractedFunctions = extractPythonEntities(code, "def")
      extractedClasses = extractPythonEntities(code, "class")
    } else if (language === "typescript") {
      const tsFn = await extractTypeScriptEntitiesTreeSitter(code, "function", resolvedPath)
      const tsClass = await extractTypeScriptEntitiesTreeSitter(code, "class", resolvedPath)
      const tsInterface = await extractTypeScriptEntitiesTreeSitter(code, "interface", resolvedPath)
      const tsType = await extractTypeScriptEntitiesTreeSitter(code, "type", resolvedPath)
      const tsEnum = await extractTypeScriptEntitiesTreeSitter(code, "enum", resolvedPath)

      if (tsFn.length > 0 || tsClass.length > 0) {
        parsingMethod = "tree-sitter"
        extractedFunctions = tsFn
        extractedClasses = [...tsClass, ...tsInterface, ...tsType, ...tsEnum]
      } else {
        // Fallback: regex
        extractedFunctions = extractTypeScriptEntities(code, "function")
        extractedClasses = [
          ...extractTypeScriptEntities(code, "class"),
          ...extractTypeScriptEntities(code, "interface"),
          ...extractTypeScriptEntities(code, "type"),
          ...extractTypeScriptEntities(code, "enum"),
        ]
      }
    } else if (language === "rust") {
      const rsFn = await extractRustEntitiesTreeSitter(code, "fn")
      const rsStruct = await extractRustEntitiesTreeSitter(code, "struct")
      const rsImpl = await extractRustEntitiesTreeSitter(code, "impl")
      const rsTrait = await extractRustEntitiesTreeSitter(code, "trait")
      const rsEnum = await extractRustEntitiesTreeSitter(code, "enum")
      const rsMod = await extractRustEntitiesTreeSitter(code, "mod")

      if (rsFn.length > 0 || rsStruct.length > 0) {
        parsingMethod = "tree-sitter"
        extractedFunctions = rsFn
        extractedClasses = [...rsStruct, ...rsImpl, ...rsTrait, ...rsEnum, ...rsMod]
      } else {
        // Fallback: regex
        extractedFunctions = extractRustEntities(code, "fn")
        extractedClasses = [
          ...extractRustEntities(code, "struct"),
          ...extractRustEntities(code, "impl"),
          ...extractRustEntities(code, "trait"),
          ...extractRustEntities(code, "enum"),
          ...extractRustEntities(code, "mod"),
        ]
      }
    }

    const functions = filterEntitiesByTarget(
      extractedFunctions,
      args.algorithm_scope === "function" ? args.target_name : undefined,
    )
    const classes = filterEntitiesByTarget(
      extractedClasses,
      args.algorithm_scope === "class" ? args.target_name : undefined,
    )
    const scopeError = validateTargetScope(
      args.algorithm_scope,
      args.target_name,
      functions,
      classes,
    )

    if (scopeError) {
      return JSON.stringify(
        {
          meta: {
            tool: "examine-algorithm",
            heuristic: true,
            agent: context.agent,
            file_path: resolvedPath,
          },
          error: scopeError,
        },
        null,
        2,
      )
    }

    const analysisSource = selectAnalysisSource(
      code,
      functions,
      classes,
      args.algorithm_scope,
    )
    const analysisLower = analysisSource.toLowerCase()
    const imports = code
      .split("\n")
      .filter((line) =>
        /^(from |import |use |export |const .*require\(|extern crate |mod \w+;)/.test(
          line.trim(),
        ),
      )
    const signals = collectSignals(analysisLower)
    const complexity = args.include_complexity
      ? estimateComplexity(analysisLower, signals)
      : null
    const patterns = args.include_patterns ? detectPatterns(analysisLower) : []
    const qualitySignals = buildQualitySignals(analysisLower, signals, language)
    const guessedTests =
      args.include_tests && resolvedPath
        ? [
            resolvedPath.replace("/src/", "/tests/test_").replace(/\.py$/, ".py"),
            resolvedPath.replace("/src/", "/tests/").replace(/\.ts$/, ".test.ts"),
            resolvedPath.replace("/src/", "/tests/").replace(/\.rs$/, "_test.rs"),
            resolvedPath.replace(/\.rs$/, "_test.rs"),
          ]
        : []

    context.metadata({
      title: `Exame estruturado: ${args.target_name ?? path.basename(resolvedPath ?? "inline")}`,
      metadata: {
        heuristic: parsingMethod === "heuristic",
        parsingMethod,
        language,
        scope: args.algorithm_scope,
      },
    })

    const result = {
      meta: {
        tool: "examine-algorithm",
        heuristic: parsingMethod === "heuristic",
        parsingMethod,
        agent: context.agent,
        directory: context.directory,
        file_path: resolvedPath,
        scope: args.algorithm_scope,
        target_name: args.target_name ?? null,
        language,
      },
      code_structure: {
        functions,
        classes,
        imports,
        total_lines: code.split("\n").length,
      },
      complexity_analysis: complexity,
      leetcode_patterns: patterns,
      test_coverage: {
        guessed_tests: guessedTests,
        missing_scenarios: [
          "happy path",
          "boundary values",
          "invalid/error paths",
          "branch alternatives",
        ],
      },
      quality_signals: qualitySignals,
      sequential_review_plan: [
        "Objetivo do algoritmo",
        "Estrategia escolhida",
        "Complexidade e memoria",
        "Casos limite",
        "Validacao e riscos",
      ],
      recommendations: buildRecommendations(signals, qualitySignals),
      analyzed_excerpt_lines: analysisSource.split("\n").length,
      disclaimer:
        "Parecer heuristico local. Confirme o resultado com leitura humana, testes e contexto de negocio.",
    }

    // Store in cache (per execucao.md Section 7.2)
    analysisCache.set(cacheKey, result)

    return JSON.stringify(result, null, 2)
  },
})
