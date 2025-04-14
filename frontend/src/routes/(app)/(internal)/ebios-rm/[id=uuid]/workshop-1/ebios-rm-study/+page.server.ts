import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { getModelInfo } from '$lib/utils/crud';
import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import type { Actions } from '@sveltejs/kit';
import { BASE_API_URL } from '$lib/utils/constants';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

export const load: PageServerLoad = async (event) => {
	const updateSchema = modelSchema('ebios-rm');
	const updatedModel: ModelInfo = getModelInfo('ebios-rm');
	const objectEndpoint = `${BASE_API_URL}/${updatedModel.endpointUrl}/${event.params.id}/object/`;
	const objectResponse = await event.fetch(objectEndpoint);
	const object = await objectResponse.json();
	const updateForm = await superValidate(object, zod(updateSchema), { errors: false });
	const detail = await loadDetail({ event, model: getModelInfo('ebios-rm'), id: event.params.id });
	return { ...detail, updateForm, updatedModel, object };
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
	},
	update: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'ebios-rm', action: 'edit' });
	}
};
