import type { ParamMatcher } from '@sveltejs/kit';
import { filterKeys } from '$lib/utils/table';

export const match = ((param) => {
	const normalizedParam = param.toLowerCase().replace(/-/g, '_');
	return filterKeys.has(normalizedParam);
}) satisfies ParamMatcher;
