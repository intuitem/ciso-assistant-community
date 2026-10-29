import { defaultDeleteFormAction, defaultWriteFormAction } from '#lib/utils/actions.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { modelSchema } from '#lib/utils/schemas.js';
import type { ModelInfo } from '#lib/utils/types.js';
import { type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

const URLModel = 'service-accounts';

export const load: PageServerLoad = async () => {
	const deleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));
	const createForm = await superValidate(zod(modelSchema(URLModel)));
	const model: ModelInfo = getModelInfo(URLModel);

	return { createForm, deleteForm, model, URLModel };
};

export const actions: Actions = {
	create: async (event) => {
		return defaultWriteFormAction({ event, urlModel: URLModel, action: 'create' });
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: URLModel });
	}
};
