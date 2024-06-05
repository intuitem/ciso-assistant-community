import { URN_REGEX } from '$lib/utils/constants';
import type { ParamMatcher } from '@sveltejs/kit';

export const match = ((param) => {
	return URN_REGEX.test(param);
}) satisfies ParamMatcher;
