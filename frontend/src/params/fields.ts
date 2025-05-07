import { listViewFields } from '$lib/utils/table';
import type { ParamMatcher } from '@sveltejs/kit';

export const match = ((param) => {
	const fields = new Set<string>();

	Object.values(listViewFields).forEach((field) => {
		if ('body' in field && field.body) {
			field.body.forEach((fieldKey) => fields.add(fieldKey));
		}
	});

	// Example output: ["folder", "lc_status", "filtering_labels"]

	return fields.has(param.toLowerCase().replace(/-/g, '_'));
}) satisfies ParamMatcher;
