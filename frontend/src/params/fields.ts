import { baseListViewFields } from '$lib/utils/table-fields';
import type { ParamMatcher } from '@sveltejs/kit';

/**
 * Validates if a route parameter matches any field key defined in the light
 * list-view field body configuration.
 *
 * This param matcher is used to verify that field names in routes like:
 * /[model]/[id]/[field] are valid fields for the given model.
 *
 * @param param - The parameter string to check
 * @returns true if the parameter matches a known field key (after normalization)
 */

const fields = new Set<string>(Object.values(baseListViewFields).flatMap((field) => field.body));

export const match = ((param) => {
	// Example fields: "folder", "lc_status", "filtering_labels", etc.

	return fields.has(param.toLowerCase().replace(/-/g, '_'));
}) satisfies ParamMatcher;
