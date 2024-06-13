import { BASE_API_URL } from '$lib/utils/constants';
import { UserEditSchema } from '$lib/utils/schemas';
import { setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';
import { getSecureRedirect } from '$lib/utils/helpers';
import { redirect, fail, type Actions } from '@sveltejs/kit';
import { getModelInfo } from '$lib/utils/crud';
import { setFlash } from 'sveltekit-flash-message/server';
import * as m from '$paraglide/messages';
import { languageTag } from '$paraglide/runtime';
import { localItems } from '$lib/utils/locales';
import { zod } from 'sveltekit-superforms/adapters';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const URLModel = 'users';
	const model = getModelInfo(URLModel);
	const objectEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;

	const object = await fetch(objectEndpoint).then((res) => res.json());
	const schema = UserEditSchema;
	const form = await superValidate(object, zod(schema));

	const foreignKeys: Record<string, any> = {};

	if (model.foreignKeyFields) {
		for (const keyField of model.foreignKeyFields) {
			const queryParams = keyField.urlParams ? `?${keyField.urlParams}` : '';
			const url = `${BASE_API_URL}/${keyField.urlModel}/${queryParams}`;
			const response = await fetch(url);
			if (response.ok) {
				foreignKeys[keyField.field] = await response.json().then((data) => data.results);
			} else {
				console.error(`Failed to fetch data for ${keyField.field}: ${response.statusText}`);
			}
		}
	}

	model.foreignKeys = foreignKeys;

	return { form, model, object };
};

export const actions: Actions = {
	default: async (event) => {
		const schema = UserEditSchema;
		const endpoint = `${BASE_API_URL}/users/${event.params.id}/`;
		const form = await superValidate(event.request, zod(schema));

		if (!form.valid) {
			console.log(form.errors);
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			if (response.error) {
				setFlash({ type: 'error', message: localItems()[response.error] }, event);
				return fail(403, { form: form });
			}
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: form });
		}
		setFlash(
			{ type: 'success', message: m.successfullyUpdatedUser({ email: form.data.email }) },
			event
		);
		redirect(
			302,
			getSecureRedirect(event.url.searchParams.get('next')) ?? `/users/${event.params.id}`
		);
	}
};
