/**
 * Server-side structured logger for the SvelteKit SSR process.
 *
 * Mirrors the backend structlog JSON shape ({ timestamp, level, logger, event, ... })
 * so backend, huey and frontend stdout share one schema for SIEM ingestion
 * (ADX / Sentinel) with no per-stream parsing.
 *
 * Output format is driven by the same LOG_FORMAT env var as the backend:
 *   - LOG_FORMAT=json  -> one JSON object per line
 *   - anything else    -> human-readable console output (default, dev-friendly)
 *
 * This module is under $lib/server so it is never bundled into the client.
 */
import { env } from '$env/dynamic/private';

type Level = 'debug' | 'info' | 'warning' | 'error' | 'critical';

const LEVEL_METHOD: Record<Level, 'debug' | 'info' | 'warn' | 'error'> = {
	debug: 'debug',
	info: 'info',
	warning: 'warn',
	error: 'error',
	critical: 'error'
};

// Snapshot the native console methods before any bridge replaces them, so the
// logger keeps writing to the real stdout/stderr even after installJsonConsole().
const nativeConsole = {
	debug: console.debug.bind(console),
	info: console.info.bind(console),
	warn: console.warn.bind(console),
	error: console.error.bind(console)
};

// Numeric severities mirror Python's logging levels so LOG_LEVEL is honoured
// identically across the backend, worker and frontend streams.
const LEVEL_SEVERITY: Record<Level, number> = {
	debug: 10,
	info: 20,
	warning: 30,
	error: 40,
	critical: 50
};

function jsonEnabled(): boolean {
	return (env.LOG_FORMAT ?? 'plain').toLowerCase() === 'json';
}

function thresholdSeverity(): number {
	const name = (env.LOG_LEVEL ?? 'INFO').toLowerCase() as Level;
	return LEVEL_SEVERITY[name] ?? LEVEL_SEVERITY.info;
}

function safeJson(value: unknown): string {
	try {
		return JSON.stringify(value);
	} catch {
		return String(value);
	}
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
	if (value === null || typeof value !== 'object') return false;
	const proto = Object.getPrototypeOf(value);
	return proto === Object.prototype || proto === null;
}

function errorToString(value: Error): string {
	return value.stack || `${value.name}: ${value.message}`;
}

// Render any Error-valued field as a stack-trace string under `exception`,
// matching structlog's format_exc_info output on the backend. This keeps a
// single error schema whether the Error arrived via logger.error('msg', { error })
// or via a bridged console.error(err) call.
function normalizeFields(fields?: Record<string, unknown>): Record<string, unknown> | undefined {
	if (!fields) return undefined;
	const out: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(fields)) {
		if (value instanceof Error) out.exception = errorToString(value);
		else out[key] = value;
	}
	return out;
}

function emit(level: Level, event: string, fields?: Record<string, unknown>): void {
	if (LEVEL_SEVERITY[level] < thresholdSeverity()) return;
	const method = nativeConsole[LEVEL_METHOD[level]];
	const normalized = normalizeFields(fields);
	if (!jsonEnabled()) {
		method(`[${level}] ${event}`, normalized && Object.keys(normalized).length ? normalized : '');
		return;
	}
	const record: Record<string, unknown> = {
		timestamp: new Date().toISOString(),
		level,
		logger: 'frontend',
		event,
		...normalized
	};
	method(JSON.stringify(record));
}

export const logger = {
	debug: (event: string, fields?: Record<string, unknown>) => emit('debug', event, fields),
	info: (event: string, fields?: Record<string, unknown>) => emit('info', event, fields),
	warning: (event: string, fields?: Record<string, unknown>) => emit('warning', event, fields),
	error: (event: string, fields?: Record<string, unknown>) => emit('error', event, fields),
	critical: (event: string, fields?: Record<string, unknown>) => emit('critical', event, fields)
};

/**
 * When LOG_FORMAT=json, wrap the global console so that *all* SSR log lines —
 * including SvelteKit internals and call sites not yet migrated to `logger` —
 * are emitted as JSON. No-op in plain mode so local dev output stays readable.
 * Idempotent: safe to call more than once.
 */
let bridgeInstalled = false;
export function installJsonConsole(): void {
	if (bridgeInstalled || !jsonEnabled()) return;
	bridgeInstalled = true;
	const bridge =
		(level: Level) =>
		(...args: unknown[]) => {
			const messages: string[] = [];
			let fields: Record<string, unknown> = {};
			for (const arg of args) {
				if (arg instanceof Error) {
					fields = { ...fields, exception: errorToString(arg) };
				} else if (isPlainObject(arg)) {
					fields = { ...fields, ...arg };
				} else if (typeof arg === 'object' && arg !== null) {
					// Arrays, Map, Set, Date, etc. don't spread into fields cleanly.
					messages.push(safeJson(arg));
				} else {
					messages.push(String(arg));
				}
			}
			emit(level, messages.join(' ').trim() || '(no message)', fields);
		};
	console.debug = bridge('debug');
	console.info = bridge('info');
	console.log = bridge('info');
	console.warn = bridge('warning');
	console.error = bridge('error');
}
