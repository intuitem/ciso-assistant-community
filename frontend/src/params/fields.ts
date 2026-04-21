import type { ParamMatcher } from '@sveltejs/kit';
import { fieldSet } from '$lib/utils/table';

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
	const normalizedParam = param.toLowerCase().replace(/-/g, '_');
	return fieldSet.has(normalizedParam);
}) satisfies ParamMatcher;
