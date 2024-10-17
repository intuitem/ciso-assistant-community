import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { SSOSettingsSchema, GeneralSettingsSchema } from '$lib/utils/schemas';
import * as m from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const settings = await fetch(`${BASE_API_URL}/settings/sso/object/`).then((res) => res.json());

	const selectOptions: Record<string, any> = {};

	const ssoModel = getModelInfo('sso-settings');
	const generalSettingModel = getModelInfo('general-settings');

	const requestList = [fetch(`${BASE_API_URL}/settings/general/info/`)];

	const selectFields = ssoModel.selectFields ?? [];
	for (const selectField of selectFields) {
		const field = selectField.field;
		const url = `${BASE_API_URL}/settings/sso/${field}/`;
		requestList.push(fetch(url).then((response) => [response, field]));
	}

	const responseList = await Promise.all(requestList);
	const generalSettingResponse = responseList[0];
	for (let i = 1; i < responseList.length; i++) {
		const [response, field] = responseList[i];
		if (response.ok) {
			selectOptions[field] = await response.json().then((data) =>
				Object.entries(data).map(([key, value]) => ({
					label: value,
					value: key
				}))
			);
		} else {
			console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
		}
	}

	ssoModel.selectOptions = selectOptions;
	const ssoForm = await superValidate(settings, zod(SSOSettingsSchema), { errors: false });
	const generalSettings = await generalSettingResponse.json();
	const generalSettingForm = await superValidate(generalSettings, zod(GeneralSettingsSchema), {
		errors: false
	});

	return { settings, ssoForm, ssoModel, generalSettingForm, generalSettingModel };
};

export const actions: Actions = {
	general: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = GeneralSettingsSchema;
		const form = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/settings/general/update/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash({ type: 'success', message: m.generalSettingsUpdated() }, event);

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
