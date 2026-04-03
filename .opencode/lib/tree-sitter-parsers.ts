/**
 * Tree-sitter parser initialization and grammar loading.
 *
 * Uses optional web-tree-sitter (WASM) with prebuilt grammars from
 * tree-sitter-typescript and tree-sitter-rust packages.
 * Lazy-initializes on first use and degrades gracefully when the dependency
 * is unavailable in the runtime environment.
 *
 * Per execucao.md Phase 2: tree-sitter as primary parser, regex as fallback.
 */
import { readFile } from "node:fs/promises"
import { createRequire } from "node:module"

type SupportedLanguage = "typescript" | "tsx" | "rust"
type TreeSitterModule = Awaited<typeof import("web-tree-sitter")>
type TreeSitterParser = InstanceType<TreeSitterModule["Parser"]>

let initialized = false
let parserModule: TreeSitterModule | null = null
const parsers = new Map<SupportedLanguage, TreeSitterParser | null>()

async function getParserModule(): Promise<TreeSitterModule | null> {
  if (parserModule) return parserModule
  try {
    parserModule = await import("web-tree-sitter")
    return parserModule
  } catch {
    return null
  }
}

async function ensureInit(): Promise<boolean> {
  if (initialized) return true
  try {
    const ParserNS = await getParserModule()
    if (!ParserNS) {
      initialized = false
      return false
    }
    await ParserNS.Parser.init()
    initialized = true
    return true
  } catch {
    initialized = false
    return false
  }
}

async function loadWasmBytes(lang: SupportedLanguage): Promise<Uint8Array | null> {
  try {
    const require = createRequire(import.meta.url)
    const wasmSpecifier =
      lang === "tsx"
        ? "tree-sitter-typescript/tree-sitter-tsx.wasm"
        : `tree-sitter-${lang}/tree-sitter-${lang}.wasm`
    const wasmPath = require.resolve(wasmSpecifier)
    const buffer = await readFile(wasmPath)
    return new Uint8Array(buffer)
  } catch {
    return null
  }
}

export async function getParser(lang: SupportedLanguage): Promise<TreeSitterParser | null> {
  if (parsers.has(lang)) {
    return parsers.get(lang) ?? null
  }

  const ok = await ensureInit()
  if (!ok) {
    parsers.set(lang, null)
    return null
  }

  const wasmBytes = await loadWasmBytes(lang)
  if (!wasmBytes) {
    parsers.set(lang, null)
    return null
  }

  try {
    const ParserNS = await getParserModule()
    if (!ParserNS) {
      parsers.set(lang, null)
      return null
    }
    const language = await ParserNS.Language.load(wasmBytes)
    const parser = new ParserNS.Parser()
    parser.setLanguage(language)
    parsers.set(lang, parser)
    return parser
  } catch {
    parsers.set(lang, null)
    return null
  }
}

export function resolveTsVariant(filePath: string | null): "typescript" | "tsx" {
  if (filePath?.endsWith(".tsx")) return "tsx"
  return "typescript"
}

export type { SupportedLanguage, TreeSitterParser }
