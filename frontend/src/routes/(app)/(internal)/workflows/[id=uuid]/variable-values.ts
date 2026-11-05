// Typed variable values as the editor shows and reads them: a default in the
// Variables panel, a seed in the run dialog. One place owns the string <->
// value rules per variable type so the two stay identical.

export type ParsedValue = { ok: true; value: unknown } | { ok: false };

/**
 * A stored value as the text of an input. `null` is an empty field. A json
 * variable always shows JSON, so a stored "hello" reads back as `"hello"`.
 */
export function formatVariableValue(value: unknown, type?: string): string {
	if (value === null || value === undefined) return '';
	return typeof value === 'string' && type !== 'json' ? value : JSON.stringify(value);
}

const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** A real calendar day: Date.parse would roll 2014-02-30 into March. */
function isCalendarDate(text: string): boolean {
	const match = DATE_RE.exec(text);
	if (!match) return false;
	const [year, month, day] = match.slice(1).map(Number);
	// setUTCFullYear, not Date.UTC: that maps years 0-99 to 1900-1999.
	const date = new Date(0);
	date.setUTCFullYear(year, month - 1, day);
	return (
		date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
	);
}

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
			return isCalendarDate(text) ? { ok: true, value: text } : { ok: false };
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
