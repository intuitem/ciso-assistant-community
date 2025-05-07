import { listViewFields } from '$lib/utils/table';
import type { ParamMatcher } from '@sveltejs/kit';

/**
 * Validates if a route parameter matches any field key defined in listViewFields.
 *
 * This param matcher is used to verify that field names in routes like:
 * /[model]/[id]/[field] are valid fields for the given model.
 *
 * @param param - The parameter string to check
 * @returns true if the parameter matches a known field key (after normalization)
 */

export const match = ((param) => {
	const fields = new Set<string>();

	Object.values(listViewFields).forEach((field) => {
		if ('body' in field && field.body) {
			field.body.forEach((fieldKey) => fields.add(fieldKey));
		}
	});

	// Example fields: "folder", "lc_status", "filtering_labels", etc.

	return fields.has(param.toLowerCase().replace(/-/g, '_'));
}) satisfies ParamMatcher;
