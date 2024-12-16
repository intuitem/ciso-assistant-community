import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { getModelInfo } from '$lib/utils/crud';
import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import type { Actions } from '@sveltejs/kit';

export const load: PageServerLoad = async (event) => {
	return await loadDetail({ event, model: getModelInfo('ebios-rm'), id: event.params.id });
};

export const actions: Actions = {
	create: async (event) => {
		return defaultWriteFormAction({
			event,
			urlModel: 'assets',
			action: 'create'
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: 'assets' });
	}
};
