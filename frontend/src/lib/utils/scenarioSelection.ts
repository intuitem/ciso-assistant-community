/**
 * Scenario selection: the risk scenario filters every view of a risk assessment
 * shares (scenario table, matrices, action plan, exports). They travel in the
 * URL behind a `scenario__` prefix so they can sit next to the action plan's own
 * control filters. See
 * documentation/architecture/decisions/risk-assessment-scenario-scope.md.
 */

export const SELECTION_PREFIX = 'scenario__';
export const LINK_TYPE_PARAM = 'link_type';
export const LINK_TYPES = ['additional', 'existing', 'all'] as const;
export type LinkType = (typeof LINK_TYPES)[number];
// The action plan is about what is still to be done: it opens on additional measures.
export const DEFAULT_LINK_TYPE: LinkType = 'additional';

export const SELECTION_FILTERS = [
	'within_tolerance',
	'treatment',
	'current_level',
	'residual_level',
	'owner',
	'threats',
	'assets',
	'qualifications',
	'filtering_labels'
] as const;
export type SelectionFilter = (typeof SELECTION_FILTERS)[number];

// Filters on related objects. An assessment can link thousands of them, so
// their options are fetched one page at a time, when the filter is opened.
export const RELATED_FILTERS = [
	'owner',
	'threats',
	'assets',
	'qualifications',
	'filtering_labels'
] as const satisfies readonly SelectionFilter[];
export type RelatedFilter = (typeof RELATED_FILTERS)[number];
export type FixedFilter = Exclude<SelectionFilter, RelatedFilter>;

export function isRelatedFilter(name: string): name is RelatedFilter {
	return (RELATED_FILTERS as readonly string[]).includes(name);
}

export type SelectionValues = Partial<Record<SelectionFilter, string[]>>;

/** `page.url.searchParams` is read-only; these helpers only read. */
type SearchParamsLike = Omit<URLSearchParams, 'append' | 'delete' | 'set' | 'sort'>;

export interface FacetOption {
	value: string;
	count: number;
	label?: string;
}

/** `GET /risk-assessments/<id>/scenario-selection/` */
export interface ScenarioSelectionData {
	count: number;
	total: number;
	ids: string[];
	filters: SelectionValues;
	ignored: { filter: string; value: string }[];
	risk_tolerance: number;
	/** Risk matrix level names, translated, indexed by level value. */
	levels: string[];
	/** Filters with a fixed set of values: every value, with its count. */
	facets: Record<FixedFilter, FacetOption[]>;
	related_filters: Record<
		RelatedFilter,
		{ has_options: boolean; selected: { value: string; label: string }[] }
	>;
}

/** `GET /risk-assessments/<id>/scenario-selection/options/` */
export interface RelatedOptionsPage {
	count: number;
	results: Required<FacetOption>[];
}

/** The selection part of a query string, prefix kept. */
export function selectionParams(search: SearchParamsLike): URLSearchParams {
	const params = new URLSearchParams();
	for (const [key, value] of search) {
		if (key.startsWith(SELECTION_PREFIX) && value !== '') params.append(key, value);
	}
	return params;
}

export function hasSelection(search: SearchParamsLike): boolean {
	return selectionParams(search).size > 0;
}

export function readSelection(search: SearchParamsLike): SelectionValues {
	const values: SelectionValues = {};
	for (const [key, value] of selectionParams(search)) {
		const name = key.slice(SELECTION_PREFIX.length) as SelectionFilter;
		(values[name] ??= []).push(value);
	}
	return values;
}

export function selectionToParams(values: SelectionValues): URLSearchParams {
	const params = new URLSearchParams();
	for (const name of SELECTION_FILTERS) {
		for (const value of values[name] ?? []) params.append(`${SELECTION_PREFIX}${name}`, value);
	}
	return params;
}

/**
 * The resolved selection as `/risk-scenarios/` filters: same names, no prefix.
 * Built from what the backend applied, not from the URL: the list endpoint
 * rejects a value the selection only ignores (a deleted threat).
 */
export function selectionListFilters(filters: Record<string, string[]> = {}): URLSearchParams {
	const params = new URLSearchParams();
	for (const [name, values] of Object.entries(filters)) {
		for (const value of values) params.append(name, value);
	}
	return params;
}

export function readLinkType(search: SearchParamsLike): LinkType {
	const value = search.get(LINK_TYPE_PARAM);
	return (LINK_TYPES as readonly string[]).includes(value ?? '')
		? (value as LinkType)
		: DEFAULT_LINK_TYPE;
}

/** `path` with `params` appended; nothing appended when `params` is empty. */
export function withParams(path: string, params: URLSearchParams | string): string {
	const query = params.toString();
	if (!query) return path;
	return `${path}${path.includes('?') ? '&' : '?'}${query}`;
}

// Per-viewer memory of the last selection, so a returning user lands on it.
// Storage can throw (private window, blocked site data): the URL stays the
// source of truth and the page works without it.
const storageKey = (riskAssessmentId: string) => `scenarioSelection:${riskAssessmentId}`;

export function rememberSelection(riskAssessmentId: string, search: SearchParamsLike) {
	try {
		const query = selectionParams(search).toString();
		if (query) localStorage.setItem(storageKey(riskAssessmentId), query);
		else localStorage.removeItem(storageKey(riskAssessmentId));
	} catch {
		// Remembering is a convenience; ignore storage failures.
	}
}

export function recallSelection(riskAssessmentId: string): URLSearchParams | null {
	try {
		const query = localStorage.getItem(storageKey(riskAssessmentId));
		if (!query) return null;
		const params = selectionParams(new URLSearchParams(query));
		return params.size > 0 ? params : null;
	} catch {
		return null;
	}
}
