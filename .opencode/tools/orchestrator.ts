#!/usr/bin/env node
/**
 * orchestrator.ts
 *
 * CLI entry point that wires together all spec-driven framework tools.
 * Provides a unified interface for:
 * - Spec registration and approval
 * - DAG compilation and execution
 * - Checkpoint/resume
 * - Traceability management
 * - Heartbeat monitoring
 * - Stagnation detection
 * - Golden trace verification
 *
 * Usage:
 *   bun run orchestrator.ts <command> [options]
 *
 * Commands:
 *   register-spec     Register a new spec
 *   approve-spec      Approve a proposed spec
 *   compile-dag       Compile DAG from approved spec
 *   run-dag           Execute DAG with checkpoint support
 *   checkpoint        Create/manage checkpoints
 *   resume            Resume from checkpoint
 *   heartbeat         Record/check heartbeats
 *   stagnation        Check for stagnation
 *   golden-trace      Compare against golden trace
 *   status            Show framework status
 *
 * This module is the main entry point for the spec-driven framework.
 */

import * as fs from 'fs';
import * as path from 'path';

// Import framework tools
import { registerSpec, approveSpec, getSpec, listSpecs, assertSpecApproved } from './spec-registry.js';
import { compileDAG } from './spec-compiler.js';
import { createLink, resolveLink, assertMinimumLinks } from './spec-linker.js';
import { buildRunManifest } from './run-manifest.js';
import { createCheckpoint, resumeFromCheckpoint, updateNodeState } from './checkpoint.js';
import { recordHeartbeat, checkHeartbeats } from './heartbeat-monitor.js';
import { checkStagnation, recordProgress } from './stagnation-detector.js';
import { registerGoldenTrace, compareAgainstGolden } from './golden-trace.js';
import { initializePersistence, saveData, loadData } from './persistence.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CommandArgs {
  command: string;
  options: Record<string, string>;
}

interface CommandResult {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
  errors?: string[];
}

// ---------------------------------------------------------------------------
// CLI Parser
// ---------------------------------------------------------------------------

function parseArgs(args: string[]): CommandArgs {
  if (args.length < 2) {
    return { command: 'help', options: {} };
  }

  const command = args[2];
  const options: Record<string, string> = {};

  for (let i = 3; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, '');
    const value = args[i + 1];
    if (value && !value.startsWith('--')) {
      options[key] = value;
    }
  }

  return { command, options };
}

// ---------------------------------------------------------------------------
// Command Handlers
// ---------------------------------------------------------------------------

async function handleRegisterSpec(options: Record<string, string>): Promise<CommandResult> {
  const { spec_id, spec_type, version, status, domain, registered_by } = options;

  if (!spec_id || !spec_type || !version || !status || !domain) {
    return {
      success: false,
      message: 'Missing required options: --spec_id, --spec_type, --version, --status, --domain',
      errors: ['Required options missing'],
    };
  }

  const payload: Record<string, unknown> = {
    spec_id,
    version,
    status,
    domain,
    ...(options.objective ? { objective: options.objective } : {}),
    ...(options.inputs ? { inputs: JSON.parse(options.inputs) } : {}),
    ...(options.outputs ? { outputs: JSON.parse(options.outputs) } : {}),
  };

  const result = await registerSpec(
    spec_id,
    spec_type as any,
    version,
    status as any,
    domain,
    payload,
    registered_by || 'cli',
  );

  return {
    success: result.valid,
    message: result.valid
      ? `Spec "${spec_id}@${version}" registered successfully`
      : `Failed to register spec: ${result.errors.join(', ')}`,
    data: result.valid ? { spec_id, version, status } : undefined,
    errors: result.valid ? undefined : result.errors,
  };
}

async function handleApproveSpec(options: Record<string, string>): Promise<CommandResult> {
  const { spec_id, version, approved_by } = options;

  if (!spec_id || !version || !approved_by) {
    return {
      success: false,
      message: 'Missing required options: --spec_id, --version, --approved_by',
      errors: ['Required options missing'],
    };
  }

  const result = await approveSpec(spec_id, version, {
    approved_by,
    requirement_refs: options.requirement_refs ? options.requirement_refs.split(',') : [],
    code_refs: options.code_refs ? options.code_refs.split(',') : [],
    test_cases: options.test_cases ? options.test_cases.split(',') : [],
    evidence_refs: options.evidence_refs ? options.evidence_refs.split(',') : [],
    owner_technical: options.owner_technical,
    owner_domain: options.owner_domain,
    approval_run_id: options.approval_run_id,
  });

  return {
    success: result.valid,
    message: result.valid
      ? `Spec "${spec_id}@${version}" approved successfully`
      : `Failed to approve spec: ${result.errors.join(', ')}`,
    data: result.valid ? { spec_id, version, traceability_link_id: (result as any).traceability_link_id } : undefined,
    errors: result.valid ? undefined : result.errors,
  };
}

async function handleCompileDAG(options: Record<string, string>): Promise<CommandResult> {
  const { spec_id, version } = options;

  if (!spec_id) {
    return {
      success: false,
      message: 'Missing required option: --spec_id',
      errors: ['Required option missing'],
    };
  }

  // Check if spec is approved
  const approvalCheck = assertSpecApproved(spec_id, version);
  if (!approvalCheck.valid) {
    return {
      success: false,
      message: `Spec not approved: ${approvalCheck.errors.join(', ')}`,
      errors: approvalCheck.errors,
    };
  }

  // Get the spec
  const spec = getSpec(spec_id, version);
  if (!spec) {
    return {
      success: false,
      message: `Spec "${spec_id}" not found`,
      errors: ['Spec not found'],
    };
  }

  // Compile DAG
  try {
    const dag = compileDAG(spec_id, version || spec.version, {
      behavior_spec: spec.payload,
      policy_bundle: {},
      verification_spec: {},
    });

    return {
      success: true,
      message: `DAG compiled successfully for "${spec_id}@${version || spec.version}"`,
      data: {
        dag_id: dag.dag_id,
        node_count: dag.nodes.length,
        edge_count: dag.edges.length,
        execution_order: dag.execution_order,
      },
    };
  } catch (error) {
    return {
      success: false,
      message: `Failed to compile DAG: ${(error as Error).message}`,
      errors: [(error as Error).message],
    };
  }
}

async function handleHeartbeat(options: Record<string, string>): Promise<CommandResult> {
  const { spec_id, run_id, node_id, action } = options;

  if (!spec_id || !run_id || !node_id) {
    return {
      success: false,
      message: 'Missing required options: --spec_id, --run_id, --node_id',
      errors: ['Required options missing'],
    };
  }

  if (action === 'record') {
    const result = await recordHeartbeat(spec_id, run_id, node_id, {
      ...(options.metadata ? JSON.parse(options.metadata) : {}),
    });

    return {
      success: result.valid,
      message: result.valid
        ? `Heartbeat recorded for node "${node_id}"`
        : `Failed to record heartbeat: ${result.errors.join(', ')}`,
      errors: result.valid ? undefined : result.errors,
    };
  }

  if (action === 'check') {
    const result = await checkHeartbeats();
    return {
      success: true,
      message: `Heartbeat check: ${result.healthy_count} healthy, ${result.stale.length} stale, ${result.dead.length} dead`,
      data: {
        healthy_count: result.healthy_count,
        stale: result.stale,
        dead: result.dead,
      },
    };
  }

  return {
    success: false,
    message: 'Invalid action. Use --action record or --action check',
    errors: ['Invalid action'],
  };
}

async function handleStagnation(options: Record<string, string>): Promise<CommandResult> {
  const { spec_id, run_id, dag_id, node_ids } = options;

  if (!spec_id || !run_id || !dag_id || !node_ids) {
    return {
      success: false,
      message: 'Missing required options: --spec_id, --run_id, --dag_id, --node_ids',
      errors: ['Required options missing'],
    };
  }

  const nodes = node_ids.split(',');
  const result = await checkStagnation(spec_id, run_id, dag_id, nodes);

  return {
    success: true,
    message: result.detected
      ? `Stagnation detected: ${result.events.length} events`
      : 'No stagnation detected',
    data: {
      detected: result.detected,
      events: result.events,
      healthy_nodes: result.healthy_nodes,
    },
  };
}

async function handleStatus(): Promise<CommandResult> {
  const specs = listSpecs();
  const persistence = initializePersistence();

  return {
    success: true,
    message: `Framework status: ${specs.length} specs registered, persistence ${persistence.success ? 'initialized' : 'not initialized'}`,
    data: {
      spec_count: specs.length,
      persistence_initialized: persistence.success,
      persistence_path: persistence.path,
    },
  };
}

function handleHelp(): CommandResult {
  return {
    success: true,
    message: `
Spec-Driven Framework CLI

Usage: bun run orchestrator.ts <command> [options]

Commands:
  register-spec     Register a new spec
                    Options: --spec_id, --spec_type, --version, --status, --domain, --registered_by

  approve-spec      Approve a proposed spec
                    Options: --spec_id, --version, --approved_by, --requirement_refs, --code_refs, --test_cases, --evidence_refs

  compile-dag       Compile DAG from approved spec
                    Options: --spec_id, --version

  heartbeat         Record or check heartbeats
                    Options: --spec_id, --run_id, --node_id, --action (record|check)

  stagnation        Check for execution stagnation
                    Options: --spec_id, --run_id, --dag_id, --node_ids (comma-separated)

  status            Show framework status

  help              Show this help message

Examples:
  bun run orchestrator.ts register-spec --spec_id capability.stable-execution --spec_type capability --version 1.0.0 --status draft --domain stable-execution
  bun run orchestrator.ts approve-spec --spec_id capability.stable-execution --version 1.0.0 --approved_by tech-lead
  bun run orchestrator.ts compile-dag --spec_id capability.stable-execution
  bun run orchestrator.ts heartbeat --spec_id capability.stable-execution --run_id run-001 --node_id node-1 --action record
  bun run orchestrator.ts stagnation --spec_id capability.stable-execution --run_id run-001 --dag_id dag-001 --node_ids node-1,node-2,node-3
  bun run orchestrator.ts status
`,
  };
}

// ---------------------------------------------------------------------------
// Main Entry Point
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs(process.argv);

  let result: CommandResult;

  switch (args.command) {
    case 'register-spec':
      result = await handleRegisterSpec(args.options);
      break;
    case 'approve-spec':
      result = await handleApproveSpec(args.options);
      break;
    case 'compile-dag':
      result = await handleCompileDAG(args.options);
      break;
    case 'heartbeat':
      result = await handleHeartbeat(args.options);
      break;
    case 'stagnation':
      result = await handleStagnation(args.options);
      break;
    case 'status':
      result = await handleStatus();
      break;
    case 'help':
    default:
      result = handleHelp();
      break;
  }

  // Output result
  console.log(JSON.stringify(result, null, 2));

  // Exit with appropriate code
  process.exit(result.success ? 0 : 1);
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export { main, parseArgs, handleRegisterSpec, handleApproveSpec, handleCompileDAG, handleHeartbeat, handleStagnation, handleStatus, handleHelp };
