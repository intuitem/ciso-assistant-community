import type { ParamMatcher } from '@sveltejs/kit';

import { THIRD_PARTY_URL_MODEL, URL_MODEL } from '$lib/utils/types';

// The generic list, detail and edit pages serve every model except those with their own
// under `[model=thirdparty_urlmodels]`. Keeping the two sets apart is what decides which
// page serves a model; were they to overlap, SvelteKit would pick by comparing route ids.
const models: readonly string[] = URL_MODEL.filter(
	(model) => !(THIRD_PARTY_URL_MODEL as readonly string[]).includes(model)
);

export const match = ((param) => {
	return models.includes(param);
}) satisfies ParamMatcher;
