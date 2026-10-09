import type { Scope } from '$lib/components/Cel/compute-assist';

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

// ---------- metric formulas (inputs are other metrics) ----------

// How an input's instances in the domain and its sub-domains combine, per
// period (mirrors metrology.series.COMBINES).
export const COMBINES = ['one', 'sum', 'avg', 'min', 'max', 'count'] as const;
export type Combine = (typeof COMBINES)[number];

export interface MetricInput {
	key: string;
	// A definition id, or a URN for a formula shipped in a library.
	definition: string;
	combine: Combine;
}

// What the expression of a metric formula may read, in input order.
export function inputReferences(inputs: unknown): string[] {
	if (!Array.isArray(inputs)) return [];
	const refs = inputs
		.map((input) => (input as Partial<MetricInput> | null)?.key)
		.filter((key): key is string => typeof key === 'string' && key.length > 0);
	return refs.length ? [...refs, 'previous'] : [];
}

// A formula reads objects (datasets) or other metrics (inputs), never both.
export function formulaKind(inputs: unknown): 'objects' | 'metrics' {
	return Array.isArray(inputs) && inputs.length ? 'metrics' : 'objects';
}

// Where a sample sits on a time axis. A metric formula's sample answers for a
// calendar period and is stamped at the period's last instant (UTC), which a
// browser east of UTC shows as the next day: plot it at the period's start
// instead, as a period is labelled. Any other sample sits at its timestamp.
export function sampleMoment(sample: { timestamp: string; period_start?: string | null }): string {
	return sample.period_start || sample.timestamp;
}

// ---------- the expression editor ----------

// What the CEL editor offers in a derived metric's expression: the datasets
// (with their aliases after a dot) or the inputs, then `previous`, and
// `metrics` for a formula over objects. Values come from the last preview
// when there is one, so a suggestion shows what the name currently holds.
export function formulaScope(
	kind: 'objects' | 'metrics',
	datasets: Record<string, unknown> | null | undefined,
	inputs: unknown,
	preview?: {
		datasets?: Record<string, unknown>;
		periods?: { inputs?: Record<string, unknown> }[];
	} | null
): Scope {
	const scope: Scope = {
		variables: [],
		referenceVariables: {},
		referenceNodes: [],
		upstreamNodes: []
	};
	if (kind === 'metrics') {
		const keys = inputReferences(inputs).filter((key) => key !== 'previous');
		const lastPeriod = preview?.periods?.length
			? preview.periods[preview.periods.length - 1]
			: undefined;
		scope.variables = keys.map((key) => ({ key, type: 'input' }));
		scope.referenceVariables = { ...(lastPeriod?.inputs ?? {}) };
	} else {
		const shapes: Record<string, Record<string, unknown>> = {};
		for (const ref of datasetReferences(datasets)) {
			const [name, alias] = ref.split('.');
			// No value until a preview answers: the suggestion shows none.
			shapes[name] = { ...(shapes[name] ?? {}), [alias]: undefined };
		}
		scope.variables = Object.keys(shapes).map((key) => ({ key, type: 'dataset' }));
		scope.referenceVariables = { ...shapes, ...(preview?.datasets ?? {}) };
		scope.variables.push({ key: 'metrics', type: 'other metrics' });
	}
	scope.variables.push({ key: 'previous', type: 'last value' });
	return scope;
}
