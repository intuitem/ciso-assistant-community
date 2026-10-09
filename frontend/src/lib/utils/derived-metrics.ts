// Helpers shared by the dataset editor and the metric definition form.

export interface AggregateRow {
	fn: string;
	field?: string;
	group_by?: string;
	as?: string;
	p?: number;
}

// The alias an aggregate answers under (mirrors core.reads.aggregates).
export function aliasOf(row: AggregateRow): string {
	if (row.as) return row.as;
	const base = row.field ? `${row.fn}_${row.field.replace(/\./g, '_')}` : row.fn;
	if (!row.group_by) return base;
	return row.fn === 'count' ? `by_${row.group_by}` : `${base}_by_${row.group_by}`;
}

// Every `dataset.alias` an expression may read, in dataset order.
export function datasetReferences(datasets: Record<string, unknown> | null | undefined): string[] {
	if (!datasets || typeof datasets !== 'object') return [];
	const refs: string[] = [];
	for (const [name, config] of Object.entries(datasets)) {
		const aggregates = (config as { aggregates?: unknown } | null)?.aggregates;
		const rows: AggregateRow[] = Array.isArray(aggregates) ? (aggregates as AggregateRow[]) : [];
		for (const row of rows) refs.push(`${name}.${aliasOf(row)}`);
	}
	return refs;
}

// Names the expression reads besides the datasets (mirrors
// metrology.derived.CONTEXT_ROOTS).
const CONTEXT_ROOTS = new Set(['previous', 'metrics', 'now', 'today']);

// What a typed dataset name becomes: identifier characters only.
export function sanitizeDatasetName(raw: string): string {
	return raw.replace(/[^A-Za-z0-9_]/g, '_');
}

// Why a dataset cannot take `name`, or null when it can. Datasets are keyed
// by name, so a duplicate would silently replace another one on save.
export function datasetNameProblem(
	name: string,
	otherNames: string[]
): 'required' | 'invalid' | 'taken' | null {
	if (!name) return 'required';
	if (!/^[A-Za-z_]/.test(name) || CONTEXT_ROOTS.has(name)) return 'invalid';
	if (otherNames.includes(name)) return 'taken';
	return null;
}
