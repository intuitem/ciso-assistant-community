// Pure helpers for an action node's config: filling the per-type defaults,
// and the read step's aggregate mode, which must not carry the row keys.

export type AggregateRow = {
	fn: string;
	field?: string;
	group_by?: string;
	as?: string;
	p?: number;
};

// Aggregate mode answers numbers, not rows: these keys are errors at publish
// time there, so switching modes adds or removes them wholesale.
export type ActionConfig = Record<string, unknown>;

export const READ_ROW_DEFAULTS: Record<string, unknown> = {
	order_by: '-created_at',
	limit: 25,
	offset: '',
	include: []
};

function isAggregateRead(config: ActionConfig): boolean {
	return config.type === 'read_objects' && config.mode === 'aggregate';
}

// Set every default the config lacks, cloned: the nested literals are shared,
// and bindings mutate them in place, so two nodes of one type would otherwise
// edit one object. An aggregate read never gets the row keys back.
export function applyActionDefaults(config: ActionConfig, defaults: object): void {
	const aggregate = isAggregateRead(config);
	for (const [key, value] of Object.entries(defaults)) {
		if (aggregate && key in READ_ROW_DEFAULTS) continue;
		if (config[key] === undefined) config[key] = structuredClone(value);
	}
}

// The aggregate rows to render. Read-only: a template must not write state,
// so a config without a list (an import, an API-authored graph) reads as
// empty until an edit creates one.
export function aggregateRowsOf(config: ActionConfig): AggregateRow[] {
	return Array.isArray(config.aggregates) ? (config.aggregates as AggregateRow[]) : [];
}

// The list an edit appends to, created on the first one.
export function ensureAggregateRows(config: ActionConfig): AggregateRow[] {
	if (!Array.isArray(config.aggregates)) config.aggregates = [];
	return config.aggregates as AggregateRow[];
}
