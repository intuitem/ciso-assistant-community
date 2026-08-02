import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) =>
	loadDetail({ event, model: getModelInfo('threat-models'), id: event.params.id });

export const actions: Actions = {
	create: async (event) =>
		defaultWriteFormAction({ event, urlModel: 'threat-models', action: 'create' }),
	edit: async (event) =>
		defaultWriteFormAction({ event, urlModel: 'threat-models', action: 'edit' }),
	delete: async (event) => defaultDeleteFormAction({ event, urlModel: 'threat-models' })
};
