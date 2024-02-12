import type { ParamMatcher } from '@sveltejs/kit';

import { URL_MODEL, type urlModel } from '$lib/utils/types';

const models = URL_MODEL;

export const match = ((param) => {
	return models.includes(param as urlModel);
}) satisfies ParamMatcher;
