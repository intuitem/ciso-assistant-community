// Typed variable values as the editor shows and reads them: a default in the
// Variables panel, a seed in the run dialog. One place owns the string <->
// value rules per variable type so the two stay identical.

export type ParsedValue = { ok: true; value: unknown } | { ok: false };

/** A stored value as the text of an input. `null` is an empty field. */
export function formatVariableValue(value: unknown): string {
	if (value === null || value === undefined) return '';
	return typeof value === 'string' ? value : JSON.stringify(value);
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * The text of an input as a stored value for `type`. An empty field means
 * "no value" (null) for every type. Text that does not fit the type is
 * rejected rather than coerced, so the editor can keep the draft and flag it.
 */
export function parseVariableValue(type: string, raw: string): ParsedValue {
	const text = raw.trim();
	if (text === '') return { ok: true, value: null };
	switch (type) {
		case 'number': {
			const parsed = Number(text);
			return Number.isFinite(parsed) ? { ok: true, value: parsed } : { ok: false };
		}
		case 'boolean':
			if (text === 'true' || text === 'false') return { ok: true, value: text === 'true' };
			return { ok: false };
		case 'date':
			return DATE_RE.test(text) && !Number.isNaN(Date.parse(text))
				? { ok: true, value: text }
				: { ok: false };
		case 'json':
			try {
				return { ok: true, value: JSON.parse(text) };
			} catch {
				return { ok: false };
			}
		default:
			return { ok: true, value: raw };
	}
}
