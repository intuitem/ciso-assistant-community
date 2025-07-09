import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { getModelInfo } from '$lib/utils/crud';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';
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
	const URLModel = 'operating-modes';
	const model = getModelInfo(URLModel);
	const detail = await loadDetail({ event, model: model, id: event.params.id });
	const updateSchema = modelSchema(URLModel);
	const objectEndpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/object/`;
	const objectResponse = await event.fetch(objectEndpoint);
	const object = await objectResponse.json();
	const updateForm = await superValidate(object, zod(updateSchema), { errors: false });

	return { ...detail, updateForm, model, object };
};

export const actions: Actions = {
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject: false });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	update: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'operating-modes', action: 'edit' });
	}
};
