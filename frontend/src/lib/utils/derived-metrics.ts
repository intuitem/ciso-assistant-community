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
// instead, as a period is labelled. A period of a day or longer starts at UTC
// midnight, which a browser west of UTC would show as the day before: it is
// placed at the browser's own midnight of that date, so the axis and the
// tooltip read the period's date whatever the time zone. Sub-daily periods
// keep their instant. Any other sample sits at its timestamp.
const UTC_MIDNIGHT = /^(\d{4})-(\d{2})-(\d{2})T00:00:00(?:\.0+)?(?:Z|\+00:00)$/;

export function sampleMoment(sample: {
	timestamp: string;
	period_start?: string | null;
}): string | number {
	const start = sample.period_start;
	if (!start) return sample.timestamp;
	const date = UTC_MIDNIGHT.exec(start);
	if (!date) return start;
	return new Date(Number(date[1]), Number(date[2]) - 1, Number(date[3])).getTime();
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

// ---------- several instances of one metric in a domain ----------

// Per input key (mirrors MetricInstance.input_choices): how the input's
// instances combine on this instance when it differs from the definition's
// default, the instance a "one value" input reads, or the instances a
// combined input leaves out.
interface InputChoice {
	combine?: Combine;
	pick?: string;
	exclude?: string[];
}
export type InputChoices = Record<string, InputChoice>;

function withChoice(
	choices: InputChoices | null | undefined,
	key: string,
	choice: InputChoice
): InputChoices | null {
	const next: InputChoices = { ...(choices ?? {}) };
	const kept = Object.fromEntries(
		Object.entries(choice).filter(([, v]) => v !== undefined && !(Array.isArray(v) && !v.length))
	) as InputChoice;
	if (Object.keys(kept).length) next[key] = kept;
	else delete next[key];
	return Object.keys(next).length ? next : null;
}

export function effectiveCombine(
	choices: InputChoices | null | undefined,
	key: string,
	defaultCombine: string
): Combine {
	return (choices?.[key]?.combine ?? defaultCombine) as Combine;
}

// Change how an input combines on this instance. A pick only means
// something for "one value", exclusions only for the other aggregates: the
// one that no longer applies is dropped.
export function setCombine(
	choices: InputChoices | null | undefined,
	key: string,
	combine: Combine,
	defaultCombine: string
): InputChoices | null {
	const current = choices?.[key] ?? {};
	return withChoice(choices, key, {
		combine: combine === defaultCombine ? undefined : combine,
		pick: combine === 'one' ? current.pick : undefined,
		exclude: combine === 'one' ? undefined : current.exclude
	});
}

export function pickInstance(
	choices: InputChoices | null | undefined,
	key: string,
	instanceId: string | null
): InputChoices | null {
	return withChoice(choices, key, { ...(choices?.[key] ?? {}), pick: instanceId ?? undefined });
}

export function excludedOf(choices: InputChoices | null | undefined, key: string): string[] {
	const excluded = choices?.[key]?.exclude;
	return Array.isArray(excluded) ? excluded : [];
}

export function pickedOf(choices: InputChoices | null | undefined, key: string): string | null {
	const picked = choices?.[key]?.pick;
	return typeof picked === 'string' ? picked : null;
}

// Include or leave out one instance of a combined input. Exclusions, not a
// list of included ones: an instance added later is read without anyone
// ticking it.
export function setIncluded(
	choices: InputChoices | null | undefined,
	key: string,
	instanceId: string,
	included: boolean
): InputChoices | null {
	const excluded = new Set(excludedOf(choices, key));
	if (included) excluded.delete(instanceId);
	else excluded.add(instanceId);
	return withChoice(choices, key, { ...(choices?.[key] ?? {}), exclude: [...excluded] });
}

// The domains that contribute more than one instance to an input: often a
// duplicate, which a sum would count twice.
export function foldersWithSeveral(instances: { folder: string }[]): string[] {
	const counts = new Map<string, number>();
	for (const { folder } of instances) counts.set(folder, (counts.get(folder) ?? 0) + 1);
	return [...counts].filter(([, n]) => n > 1).map(([folder]) => folder);
}

// ---------- a computed metric started from instances ----------

// The name a picked instance takes in the formula: its metric's name as an
// identifier, so the definition reads as a reusable formula (`clicks /
// headcount`), suffixed when two picks share a metric.
export function formulaKey(metricName: string, taken: string[] = []): string {
	let key = (metricName ?? '')
		.normalize('NFKD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '_')
		.replace(/^_+|_+$/g, '')
		.slice(0, 40)
		.replace(/_+$/, '');
	if (!key) key = 'metric';
	if (/^[0-9]/.test(key)) key = `m_${key}`;
	if (CONTEXT_ROOTS.has(key)) key = `${key}_value`;
	let candidate = key;
	for (let n = 2; taken.includes(candidate); n++) candidate = `${key}_${n}`;
	return candidate;
}

// The expression with every reference to `from` now reading `to`. Only whole
// names: not `from_x`, not a field after a dot, not inside a string.
export function renameReference(expression: string, from: string, to: string): string {
	if (!from || from === to) return expression;
	const parts = expression.split(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/);
	const name = new RegExp(`(?<![\\w.])${from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?!\\w)`, 'g');
	return parts.map((part, i) => (i % 2 ? part : part.replace(name, to))).join('');
}

export type QuickFormula = 'sum' | 'ratio' | 'difference' | 'average';

// One click to a common formula over the picks, for the author to adjust.
export function quickFormulas(keys: string[]): { kind: QuickFormula; expression: string }[] {
	if (keys.length < 2) return [];
	const formulas: { kind: QuickFormula; expression: string }[] = [];
	if (keys.length === 2) {
		formulas.push({ kind: 'ratio', expression: `${keys[0]} * 100.0 / ${keys[1]}` });
		formulas.push({ kind: 'difference', expression: `${keys[0]} - ${keys[1]}` });
	}
	formulas.push({ kind: 'sum', expression: keys.join(' + ') });
	formulas.push({
		kind: 'average',
		expression: `(${keys.join(' + ')}) / ${keys.length}.0`
	});
	return formulas;
}

// A select's value once its options change: the author's choice while it is
// still offered, else the first option.
export function keepOrFirst(current: string, offered: { id: string }[]): string {
	return offered.some((o) => o.id === current) ? current : (offered[0]?.id ?? '');
}

// The list with the item at `from` moved to `to`, the others keeping their
// order. Out-of-range positions leave it as it was.
export function moveItem<T>(items: T[], from: number, to: number): T[] {
	if (from === to || from < 0 || to < 0 || from >= items.length || to >= items.length) return items;
	const next = [...items];
	const [item] = next.splice(from, 1);
	next.splice(to, 0, item);
	return next;
}

// ---------- the preview's small chart ----------

export interface SparkPoint {
	x: number;
	y: number;
	start: string;
	value: number;
}

// A small time series of the preview's periods, drawn in a `width` by
// `height` box: the numeric periods as points (a skipped one leaves its slot
// empty, so the spacing stays true to time), the line through them and the
// area under it. Null with fewer than two numbers: nothing to draw a trend of.
// `range` puts two lines on one scale (sparkRange): a before/after chart.
export function sparkline(
	periods: { start: string; value: unknown; skipped?: boolean }[],
	width: number,
	height: number,
	pad = 4,
	range?: { min: number; max: number } | null
): { points: SparkPoint[]; line: string; area: string } | null {
	const slots = periods.length;
	const numeric = periods
		.map((period, index) => ({ period, index }))
		.filter(({ period }) => isPlotted(period));
	if (numeric.length < 2) return null;
	const values = numeric.map(({ period }) => period.value as number);
	const min = range ? range.min : Math.min(...values);
	const max = range ? range.max : Math.max(...values);
	const span = max - min;
	const step = slots > 1 ? (width - 2 * pad) / (slots - 1) : 0;
	const points = numeric.map(({ period, index }) => {
		const value = period.value as number;
		// A flat series sits mid-height rather than on the floor.
		const ratio = span ? (value - min) / span : 0.5;
		return {
			x: +(pad + index * step).toFixed(2),
			y: +(height - pad - ratio * (height - 2 * pad)).toFixed(2),
			start: period.start,
			value
		};
	});
	const line = points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
	const first = points[0];
	const last = points[points.length - 1];
	const area = `${line} L${last.x},${height} L${first.x},${height} Z`;
	return { points, line, area };
}

function isPlotted(period: { value: unknown; skipped?: boolean }): boolean {
	return !period.skipped && typeof period.value === 'number' && Number.isFinite(period.value);
}

// The scale several series share: the lowest and highest of their numbers.
export function sparkRange(
	...series: { value: unknown; skipped?: boolean }[][]
): { min: number; max: number } | null {
	const values = series
		.flat()
		.filter(isPlotted)
		.map((period) => period.value as number);
	return values.length ? { min: Math.min(...values), max: Math.max(...values) } : null;
}

// What a metric holds now, on a preview's periods: its samples matched by
// period start, so the now and new lines of a comparison share their slots.
// `read` turns a sample's value into the number to plot, or null.
export function samplesOnPeriods(
	periods: { start: string }[],
	samples: { timestamp: string; period_start?: string | null; value: unknown }[],
	read: (value: Record<string, unknown>) => unknown
): { start: string; value: unknown; skipped: boolean }[] {
	const held = new Map<number, unknown>();
	for (const sample of samples) {
		let value = sample.value;
		try {
			if (typeof value === 'string') value = JSON.parse(value);
		} catch {
			continue;
		}
		if (!value || typeof value !== 'object') continue;
		// Matched on the period's own instant, not where a chart plots it.
		const moment = Date.parse(sample.period_start || sample.timestamp);
		if (!Number.isNaN(moment) && !held.has(moment)) {
			held.set(moment, read(value as Record<string, unknown>));
		}
	}
	return periods.map((period) => {
		const value = held.get(Date.parse(period.start));
		return { start: period.start, value: value ?? null, skipped: value === undefined };
	});
}

// How the latest numeric period moved from the one before, and whether that
// is good news for this metric. Null without two numbers to compare.
export function latestTrend(
	periods: { value: unknown; skipped?: boolean }[],
	higherIsBetter: boolean
): { delta: number; good: boolean | null } | null {
	const values = periods
		.filter((p) => !p.skipped && typeof p.value === 'number' && Number.isFinite(p.value))
		.map((p) => p.value as number);
	if (values.length < 2) return null;
	const delta = values[values.length - 1] - values[values.length - 2];
	return { delta, good: delta === 0 ? null : delta > 0 === higherIsBetter };
}

// ---------- a level (qualitative) result ----------

export interface Level {
	ref_id: string;
	name: string;
	// Read from the formula, not typed in: it goes when the formula stops
	// returning it.
	auto?: boolean;
}

const STRING_LITERAL = /"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'/g;

// The quoted texts of an expression, in order, each once (mirrors
// metrology.compose.string_literals). Inputs are numbers, so in a level
// formula these are the levels it returns.
export function stringLiterals(expression: string): string[] {
	const seen: string[] = [];
	for (const match of (expression ?? '').matchAll(STRING_LITERAL)) {
		const text = match[1] ?? match[2] ?? '';
		if (!seen.includes(text)) seen.push(text);
	}
	return seen;
}

function answersTo(level: Level, text: string): boolean {
	const t = text.trim().toLowerCase();
	return level.name.trim().toLowerCase() === t || level.ref_id.trim().toLowerCase() === t;
}

// The levels once the formula returns `texts`: the author's levels and order
// stay, a level read from the formula goes when the formula drops it, and a
// new text is added at the end.
export function syncLevels(levels: Level[], texts: string[]): Level[] {
	const kept = levels.filter((level) => !level.auto || texts.some((t) => answersTo(level, t)));
	const taken = kept.flatMap((level) => [level.ref_id.toLowerCase(), level.name.toLowerCase()]);
	const added: Level[] = [];
	for (const text of texts) {
		if (!text.trim() || kept.some((level) => answersTo(level, text))) continue;
		const ref_id = formulaKey(text, taken);
		taken.push(ref_id, text.toLowerCase());
		added.push({ ref_id, name: text, auto: true });
	}
	return added.length || kept.length !== levels.length ? [...kept, ...added] : levels;
}

// Texts the formula returns that no level answers to.
export function unknownLevels(expression: string, levels: Level[]): string[] {
	return stringLiterals(expression).filter((text) => !levels.some((l) => answersTo(l, text)));
}

// The expression with every quoted `from` now quoting `to`.
export function renameLiteral(expression: string, from: string, to: string): string {
	if (!from || from === to) return expression;
	return expression.replace(STRING_LITERAL, (whole, double, single) => {
		const text = double ?? single;
		if (text !== from) return whole;
		return double !== undefined ? `"${to}"` : `'${to}'`;
	});
}

// The 1-based position of the level a result names (its name, its ref_id or
// its position, as the backend reads it), or null.
export function levelIndex(value: unknown, levels: Level[]): number | null {
	if (typeof value === 'number') {
		return Number.isInteger(value) && value >= 1 && value <= levels.length ? value : null;
	}
	if (typeof value !== 'string') return null;
	const index = levels.findIndex((level) => answersTo(level, value));
	return index === -1 ? null : index + 1;
}

// A starting point for a level formula over the picks.
export function levelStarter(keys: string[]): string {
	if (!keys.length) return '';
	const measure = keys.length >= 2 ? `${keys[0]} * 100.0 / ${keys[1]}` : keys[0];
	// Worst level first: the levels fill in the order the texts appear, and
	// "higher is better" (ticked by default) makes the last one the best.
	return `${measure} < 50.0 ? "Low" : "High"`;
}
