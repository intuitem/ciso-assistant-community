// Authoring help for compute rows: what a CEL expression can reference at the
// cursor. Pure functions so the
// popover component stays thin and this stays unit-testable.

import { dig } from './expressions';

export type SuggestionKind = 'variable' | 'seed' | 'loop' | 'path' | 'function' | 'macro';

export type Suggestion = {
	/** What the list shows. */
	text: string;
	kind: SuggestionKind;
	/** Type, signature or reference value, muted next to the text. */
	detail?: string;
	/** What replaces the current token. */
	insert: string;
	/** How many characters before the end of `insert` the cursor lands (inside parens). */
	cursorBack?: number;
};

export type Scope = {
	variables: { key: string; type?: string }[];
	referenceVariables: Record<string, unknown>;
	referenceNodes: { key: string; label: string; output: unknown }[];
	upstreamNodes: {
		ref: string;
		label: string;
		isLoop?: boolean;
		actionConfig?: Record<string, unknown>;
	}[];
};

// CEL's own plus the helpers the compute action registers (see
// backend/automation/workflows/expressions.py). Signatures are for display.
export const FUNCTIONS: { name: string; signature: string }[] = [
	{ name: 'sum', signature: 'sum(list)' },
	{ name: 'avg', signature: 'avg(list)' },
	{ name: 'min', signature: 'min(list)' },
	{ name: 'max', signature: 'max(list)' },
	{ name: 'round', signature: 'round(x, digits?)' },
	{ name: 'floor', signature: 'floor(x)' },
	{ name: 'ceil', signature: 'ceil(x)' },
	{ name: 'abs', signature: 'abs(x)' },
	{ name: 'size', signature: 'size(list | string | map)' },
	{ name: 'has', signature: 'has(a.b)' },
	{ name: 'int', signature: 'int(x)' },
	{ name: 'double', signature: 'double(x)' },
	{ name: 'string', signature: 'string(x)' },
	{ name: 'timestamp', signature: "timestamp('2026-01-01T00:00:00Z')" },
	{ name: 'duration', signature: "duration('72h')" }
];

// Methods offered after a dot, by the kind of value the base resolves to.
const LIST_MACROS: { name: string; insert: string; signature: string }[] = [
	{ name: 'map', insert: 'map(x, )', signature: 'map(x, expr)' },
	{ name: 'filter', insert: 'filter(x, )', signature: 'filter(x, cond)' },
	{ name: 'exists', insert: 'exists(x, )', signature: 'exists(x, cond)' },
	{ name: 'all', insert: 'all(x, )', signature: 'all(x, cond)' },
	{ name: 'size', insert: 'size()', signature: 'size()' }
];
const STRING_METHODS: { name: string; insert: string; signature: string }[] = [
	{ name: 'contains', insert: 'contains()', signature: "contains('x')" },
	{ name: 'startsWith', insert: 'startsWith()', signature: "startsWith('x')" },
	{ name: 'endsWith', insert: 'endsWith()', signature: "endsWith('x')" },
	{ name: 'matches', insert: 'matches()', signature: "matches('re')" },
	{ name: 'size', insert: 'size()', signature: 'size()' }
];

const TOKEN_CHARS = /[A-Za-z0-9_.]/;
const MAX_SUGGESTIONS = 8;

/**
 * The identifier path around the cursor. `text` is what was typed up to the
 * cursor (what suggestions match); `end` extends over the rest of the word, so
 * accepting a suggestion replaces the whole word: `likel|ihood` becomes
 * `likelihood`, not `likelihoodihood`.
 */
export function currentToken(
	value: string,
	cursor: number
): { start: number; end: number; text: string } {
	const at = Math.max(0, Math.min(cursor, value.length));
	let start = at;
	while (start > 0 && TOKEN_CHARS.test(value[start - 1])) start -= 1;
	let end = at;
	while (end < value.length && TOKEN_CHARS.test(value[end])) end += 1;
	return { start, end, text: value.slice(start, at) };
}

export function shortValue(value: unknown, max = 24): string {
	if (value === undefined) return '';
	const text = typeof value === 'string' ? JSON.stringify(value) : (JSON.stringify(value) ?? '');
	return text.length > max ? text.slice(0, max - 1) + '…' : text;
}

function referenceContext(scope: Scope): Record<string, unknown> {
	return {
		...scope.referenceVariables,
		nodes: Object.fromEntries(scope.referenceNodes.map((n) => [n.key, n.output]))
	};
}

function startsWithCi(text: string, prefix: string): boolean {
	return text.toLowerCase().startsWith(prefix.toLowerCase());
}

function rootSuggestions(partial: string, scope: Scope): Suggestion[] {
	const out: Suggestion[] = [];
	const context = referenceContext(scope);
	for (const variable of scope.variables) {
		const value = scope.referenceVariables[variable.key];
		const detail = [variable.type, shortValue(value)].filter(Boolean).join(' ');
		out.push({ text: variable.key, kind: 'variable', detail, insert: variable.key });
	}
	for (const seed of ['today', 'now']) {
		out.push({ text: seed, kind: 'seed', detail: shortValue(context[seed]), insert: seed });
	}
	if ('payload' in scope.referenceVariables) {
		out.push({ text: 'payload', kind: 'seed', detail: 'trigger payload', insert: 'payload.' });
	}
	if (scope.upstreamNodes.length || scope.referenceNodes.length) {
		out.push({ text: 'nodes', kind: 'path', detail: 'step outputs', insert: 'nodes.' });
	}
	if (scope.upstreamNodes.some((n) => n.isLoop)) {
		out.push({ text: 'item', kind: 'loop', detail: 'loop element', insert: 'item' });
		out.push({ text: 'index', kind: 'loop', detail: 'loop position', insert: 'index' });
	}
	for (const fn of FUNCTIONS) {
		out.push({
			text: fn.name,
			kind: 'function',
			detail: fn.signature,
			insert: `${fn.name}()`,
			cursorBack: 1
		});
	}
	return out.filter((s) => startsWithCi(s.text, partial));
}

function memberSuggestions(base: string, partial: string, scope: Scope): Suggestion[] {
	const out: Suggestion[] = [];
	const context = referenceContext(scope);
	if (base === 'nodes') {
		const seen = new Set<string>();
		for (const node of [
			...scope.referenceNodes.map((n) => ({ ref: n.key, label: n.label })),
			...scope.upstreamNodes.map((n) => ({ ref: n.ref, label: n.label }))
		]) {
			if (!node.ref || seen.has(node.ref)) continue;
			seen.add(node.ref);
			out.push({ text: node.ref, kind: 'path', detail: node.label, insert: `nodes.${node.ref}.` });
		}
	} else {
		const resolved = dig(context, base);
		if (Array.isArray(resolved)) {
			for (const macro of LIST_MACROS) {
				out.push({
					text: macro.name,
					kind: 'macro',
					detail: macro.signature,
					insert: `${base}.${macro.insert}`,
					cursorBack: 1
				});
			}
		} else if (typeof resolved === 'string') {
			for (const method of STRING_METHODS) {
				out.push({
					text: method.name,
					kind: 'macro',
					detail: method.signature,
					insert: `${base}.${method.insert}`,
					cursorBack: 1
				});
			}
		} else if (resolved && typeof resolved === 'object') {
			for (const [key, value] of Object.entries(resolved as Record<string, unknown>)) {
				const nested = value && typeof value === 'object' && !Array.isArray(value);
				out.push({
					text: key,
					kind: 'path',
					detail: shortValue(value),
					insert: `${base}.${key}${nested ? '.' : ''}`
				});
			}
		}
	}
	return out.filter((s) => startsWithCi(s.text, partial));
}

/** Suggestions for the token at the cursor; empty when nothing useful applies. */
export function buildSuggestions(token: string, scope: Scope): Suggestion[] {
	if (!token) return [];
	const dot = token.lastIndexOf('.');
	const suggestions =
		dot === -1
			? rootSuggestions(token, scope)
			: memberSuggestions(token.slice(0, dot), token.slice(dot + 1), scope);
	return suggestions.slice(0, MAX_SUGGESTIONS);
}

/** Replace the token spanning [tokenStart, tokenEnd) with the suggestion. */
export function applySuggestion(
	value: string,
	tokenStart: number,
	tokenEnd: number,
	suggestion: Suggestion
): { value: string; cursor: number } {
	const next = value.slice(0, tokenStart) + suggestion.insert + value.slice(tokenEnd);
	return {
		value: next,
		cursor: tokenStart + suggestion.insert.length - (suggestion.cursorBack ?? 0)
	};
}
