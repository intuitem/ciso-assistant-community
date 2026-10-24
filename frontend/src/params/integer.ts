import type { ParamMatcher } from '@sveltejs/kit';

export const match = ((param) => {
	return /^[1-9]\d*$/.test(param);
}) satisfies ParamMatcher;
