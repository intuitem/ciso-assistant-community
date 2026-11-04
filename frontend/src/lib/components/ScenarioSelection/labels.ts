import { safeTranslate } from '#lib/utils/i18n.js';
import { m } from '#paraglide/messages.js';
import {
	SELECTION_FILTERS,
	type ScenarioSelectionData,
	type SelectionFilter,
	type SelectionValues
} from '#lib/utils/scenarioSelection.js';

export const FILTER_LABELS: Record<SelectionFilter, () => string> = {
	within_tolerance: m.withinTolerance,
	treatment: m.treatment,
	current_level: m.currentLevel,
	residual_level: m.residualLevel,
	owner: m.owners,
	threats: m.threats,
	assets: m.assets,
	qualifications: m.qualifications,
	filtering_labels: m.labels
};

export function filterLabel(name: string): string {
	return name in FILTER_LABELS ? FILTER_LABELS[name as SelectionFilter]() : safeTranslate(name);
}

export function optionLabel(
	name: SelectionFilter,
	value: string,
	selection: ScenarioSelectionData | null
): string {
	if (name === 'within_tolerance')
		return value === 'YES' ? m.yes() : value === 'NO' ? m.no() : '--';
	if (name === 'treatment') return safeTranslate(value);
	if (name === 'current_level' || name === 'residual_level')
		return selection?.levels?.[Number(value)] ?? '--';
	return selection?.facets?.[name]?.find((o) => o.value === value)?.label ?? value;
}

/** One "Filter: value, value" line per active filter, for summaries. */
export function selectionSummary(
	values: SelectionValues,
	selection: ScenarioSelectionData | null
): string[] {
	return SELECTION_FILTERS.filter((name) => (values[name]?.length ?? 0) > 0).map(
		(name) =>
			`${m.selectionFilterLabel({ filter: FILTER_LABELS[name]() })} ${(values[name] ?? [])
				.map((v) => optionLabel(name, v, selection))
				.join(', ')}`
	);
}
