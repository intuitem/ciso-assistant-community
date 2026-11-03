import { defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { error, type Actions, type NumericRange } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

const URLModel = 'connection-profiles';

export const load: PageServerLoad = async (event) => {
	const model = getModelInfo(URLModel);
	const res = await event.fetch(`${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const object = await res.json();
	const form = await superValidate(object, zod(modelSchema(URLModel)), { errors: false });
	return { form, model, object, URLModel, title: m.edit() };
};

export const actions: Actions = {
	default: async (event) => {
		return defaultWriteFormAction({ event, urlModel: URLModel, action: 'edit' });
	}
};
