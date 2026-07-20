// Client-side mirror of the engine's template semantics (workflows/actions.py:
// dig + render), used for the builder's live preview. Keep in sync.

const TEMPLATE_RE = /\{\{\s*([\w.]+)\s*\}\}/g;

export function dig(data: unknown, path: string): unknown {
	let current: any = data;
	for (const part of String(path).split('.')) {
		if (current !== null && typeof current === 'object' && !Array.isArray(current)) {
			if (!(part in current)) return undefined;
			current = current[part];
		} else if (Array.isArray(current) && /^\d+$/.test(part) && Number(part) < current.length) {
			current = current[Number(part)];
		} else {
			return undefined;
		}
	}
	return current;
}

export function renderTemplate(value: string, context: Record<string, unknown>): string {
	return value.replace(TEMPLATE_RE, (_match, path: string) => {
		const resolved = dig(context, path);
		if (resolved === undefined || resolved === null) return '';
		// Mirror the engine: objects/lists serialize as JSON.
		return typeof resolved === 'object' ? JSON.stringify(resolved) : String(resolved);
	});
}

export function previewValue(value: unknown, maxLength = 42): string {
	if (value === null || value === undefined) return 'null';
	const text = typeof value === 'string' ? value : JSON.stringify(value);
	return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text;
}

export function isExpandable(value: unknown): boolean {
	return (
		value !== null &&
		typeof value === 'object' &&
		Object.keys(value as object).length > 0
	);
}

export function childEntries(value: unknown): [string, unknown][] {
	if (Array.isArray(value)) return value.map((item, index) => [String(index), item]);
	if (value !== null && typeof value === 'object')
		return Object.entries(value as Record<string, unknown>);
	return [];
}
