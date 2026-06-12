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

function jsonEnabled(): boolean {
	return (env.LOG_FORMAT ?? 'plain').toLowerCase() === 'json';
}

function serializeError(value: unknown): Record<string, unknown> {
	if (value instanceof Error) {
		return { exception: value.stack || `${value.name}: ${value.message}` };
	}
	return { error: typeof value === 'string' ? value : safeJson(value) };
}

function safeJson(value: unknown): string {
	try {
		return JSON.stringify(value);
	} catch {
		return String(value);
	}
}

function emit(level: Level, event: string, fields?: Record<string, unknown>): void {
	const method = nativeConsole[LEVEL_METHOD[level]];
	if (!jsonEnabled()) {
		method(`[${level}] ${event}`, fields && Object.keys(fields).length ? fields : '');
		return;
	}
	const record: Record<string, unknown> = {
		timestamp: new Date().toISOString(),
		level,
		logger: 'frontend',
		event,
		...fields
	};
	// JSON.stringify renders Error instances as {}; surface name/message/stack instead.
	method(
		JSON.stringify(record, (_key, value) =>
			value instanceof Error
				? { name: value.name, message: value.message, stack: value.stack }
				: value
		)
	);
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
					fields = { ...fields, ...serializeError(arg) };
				} else if (arg && typeof arg === 'object') {
					fields = { ...fields, ...(arg as Record<string, unknown>) };
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
