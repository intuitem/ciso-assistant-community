import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { SSOSettingsSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import * as m from '$paraglide/messages';

export const load: PageServerLoad = async ({ fetch }) => {
	const settings = await fetch(`${BASE_API_URL}/settings/sso/object/`).then((res) => res.json());

	const selectOptions: Record<string, any> = {};

	const model = getModelInfo('sso-settings');

	if (model.selectFields) {
		for (const selectField of model.selectFields) {
			const url = `${BASE_API_URL}/settings/sso/${selectField.field}/`;
			const response = await fetch(url);
			if (response.ok) {
				selectOptions[selectField.field] = await response.json().then((data) =>
					Object.entries(data).map(([key, value]) => ({
						label: value,
						value: key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
		}
	}

	model.selectOptions = selectOptions;

	const form = await superValidate(settings, zod(SSOSettingsSchema), { errors: false });
	return { settings, form, model };
};

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = SSOSettingsSchema;
		const form = await superValidate(formData, zod(schema));
		// NOTE: /sso had-coded for development
		const endpoint = `${BASE_API_URL}/settings/sso/`;

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response: Record<string, any> = await res.json();
			console.error(response);
			if (response.warning) {
				setFlash({ type: 'warning', message: response.warning }, event);
				return { form };
			}
			if (response.error) {
				setFlash({ type: 'error', message: response.error }, event);
				return { form };
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, value);
			});
			return fail(400, { form });
		}
		setFlash({ type: 'success', message: m.ssoSettingsupdated() }, event);
	}
};
