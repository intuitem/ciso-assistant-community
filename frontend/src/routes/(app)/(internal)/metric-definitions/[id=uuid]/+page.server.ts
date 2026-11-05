import { getModelInfo } from '#lib/utils/crud.js';
import { loadDetail } from '#lib/utils/load.js';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '#lib/utils/actions.js';

export const load: PageServerLoad = async (event) => {
	return loadDetail({
		event,
		model: getModelInfo('metric-definitions'),
		id: event.params.id
	});
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
