import { listViewFields } from '$lib/utils/table';
import type { ParamMatcher } from '@sveltejs/kit';

export const match = ((param) => {
	const filterKeys = new Set<string>();

	Object.values(listViewFields).forEach((field) => {
		if ('filters' in field && field.filters) {
			Object.keys(field.filters).forEach((filterKey) => filterKeys.add(filterKey));
		}
	});

	// Example output: ["folder", "lc_status", "filtering_labels"]

	return filterKeys.has(param.toLowerCase().replace(/-/g, '_'));
}) satisfies ParamMatcher;
