import type { ParamMatcher } from '@sveltejs/kit';

export const match = ((param) => {
	return /^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$/.test(
		param
	);
}) satisfies ParamMatcher;
