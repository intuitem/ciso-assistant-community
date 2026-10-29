import { getModelInfo } from '#lib/utils/crud.js';
import { loadDetail } from '#lib/utils/load.js';
import { type Actions } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';
import { nestedDeleteFormAction } from '#lib/utils/actions.js';

export const load: PageServerLoad = async (event) => {
	return await loadDetail({ event, model: getModelInfo('evidences'), id: event.params.id });
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
