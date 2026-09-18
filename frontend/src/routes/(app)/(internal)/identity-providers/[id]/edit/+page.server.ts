import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { getSecureRedirect } from '$lib/utils/helpers';
import { safeTranslate } from '$lib/utils/i18n';
import { modelSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { error, fail, redirect, type Actions, type NumericRange } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { message, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

const URLModel = 'identity-providers';

export const load: PageServerLoad = async (event) => {
	const model = getModelInfo(URLModel);
	const schema = modelSchema(URLModel);

	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`;
	const res = await event.fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const socialApp = await res.json();
	const object = {
		name: socialApp.name,
		provider_id: socialApp.provider_id,
		client_id: socialApp.client_id,
		server_url: socialApp.server_url
	};

	const form = await superValidate(object, zod(schema), { errors: false });

	return { form, model, object, URLModel, title: m.edit() };
};

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = modelSchema(URLModel);
		const form = await superValidate(formData, zod(schema));

		if (!form.valid) {
			console.error(form.errors);
			return message(form, { status: 400 });
		}

		const model = getModelInfo(URLModel);
		const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`;

		const res = await event.fetch(endpoint, {
			method: 'PATCH',
			body: JSON.stringify(form.data)
		});

		if (!res.ok) return await handleErrorResponse({ event, response: res, form });

		const writtenObject = await res.json();

		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({
					object: safeTranslate(model.verboseName).toLowerCase()
				})
			},
			event
		);

		const next = getSecureRedirect(event.url.searchParams.get('next'));
		if (next) redirect(302, next);

		return message(form, { object: writtenObject });
	}
};
