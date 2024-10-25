import type { ParamMatcher } from '@sveltejs/kit';

import { THIRD_PARTY_URL_MODEL, type thirdPartyUrlModel } from '$lib/utils/types';

const models = THIRD_PARTY_URL_MODEL;

export const match = ((param) => {
	return models.includes(param as thirdPartyUrlModel);
}) satisfies ParamMatcher;
