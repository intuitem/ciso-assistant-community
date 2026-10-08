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
export function datasetReferences(datasets: Record<string, any> | null | undefined): string[] {
	if (!datasets || typeof datasets !== 'object') return [];
	const refs: string[] = [];
	for (const [name, config] of Object.entries(datasets)) {
		const rows: AggregateRow[] = Array.isArray(config?.aggregates) ? config.aggregates : [];
		for (const row of rows) refs.push(`${name}.${aliasOf(row)}`);
	}
	return refs;
}
