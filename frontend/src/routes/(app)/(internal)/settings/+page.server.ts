import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { SSOSettingsSchema, GlobalSettingsSchema } from '$lib/utils/schemas';
import * as m from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const settings = await fetch(`${BASE_API_URL}/settings/sso/object/`).then((res) => res.json());

	const selectOptions: Record<string, any> = {};

	const ssoMmodel = getModelInfo('sso-settings');
	const globalSettingsModel = getModelInfo('global-settings');

	if (ssoMmodel.selectFields) {
		for (const selectField of ssoMmodel.selectFields) {
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

	ssoMmodel.selectOptions = selectOptions;

	const ssoForm = await superValidate(settings, zod(SSOSettingsSchema), { errors: false });
	const globalSettingsForm = await superValidate(settings, zod(GlobalSettingsSchema), {
		errors: false
	});

	return { settings, ssoForm, ssoMmodel, globalSettingsForm, globalSettingsModel };
};

export const actions: Actions = {
	global: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = GlobalSettingsSchema;
		const form = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/settings/global/update/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		// Make the translation
		// It must be called m.globalSettingsUpdated()
		setFlash({ type: 'success', message: m.ssoSettingsUpdated() }, event);

		return { form };
	},
	sso: async (event) => {
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

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash({ type: 'success', message: m.ssoSettingsUpdated() }, event);

		return { form };
	}
};
