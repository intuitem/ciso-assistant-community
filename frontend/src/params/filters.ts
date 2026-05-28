import { baseListViewFields } from '$lib/utils/table-metadata';
import type { ParamMatcher } from '@sveltejs/kit';

const filterKeys = new Set<string>(
	Object.values(baseListViewFields).flatMap((field) => ('filters' in field ? field.filters : []))
);

export const match = ((param) => {
	// Example output: ["folder", "lc_status", "filtering_labels"]

	return filterKeys.has(param.toLowerCase().replace(/-/g, '_'));
}) satisfies ParamMatcher;
