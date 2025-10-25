import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { SSOSettingsSchema, GeneralSettingsSchema, FeatureFlagsSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const ssoSettings = await fetch(`${BASE_API_URL}/settings/sso/object/`).then((res) => res.json());
	const generalSettings = await fetch(`${BASE_API_URL}/settings/general/object/`).then((res) =>
		res.json()
	);
	const featureFlagSettings = await fetch(`${BASE_API_URL}/settings/feature-flags/`).then((res) =>
		res.json()
	);

	const selectOptions: Record<string, any> = {};

	const ssoModel = getModelInfo('sso-settings');
	const generalSettingModel = getModelInfo('general-settings');
	const featureFlagModel = getModelInfo('feature-flags');

	if (ssoModel.selectFields) {
		for (const selectField of ssoModel.selectFields) {
			const url = `${BASE_API_URL}/settings/sso/${selectField.field}/`;
			const response = await fetch(url);
			if (response.ok) {
				selectOptions[selectField.field] = await response.json().then((data) =>
					Object.entries(data).map(([key, value]) => ({
						label: value,
						value: selectField.valueType === 'number' ? parseInt(key) : key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
		}
	}

	ssoModel.selectOptions = selectOptions;

	if (featureFlagModel.selectFields) {
		for (const selectField of featureFlagModel.selectFields) {
			const url = `${BASE_API_URL}/settings/feature-flags/feature_flags/`;
			const response = await fetch(url);
			if (response.ok) {
				selectOptions[selectField.field] = await response.json().then((data) =>
					Object.entries(data).map(([key, value]) => ({
						label: value,
						value: selectField.valueType === 'number' ? parseInt(key) : key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
		}
	}
	featureFlagModel.selectOptions = selectOptions;

	if (generalSettingModel.selectFields) {
		for (const selectField of generalSettingModel.selectFields) {
			const url = `${BASE_API_URL}/settings/general/${selectField.field}/`;
			const response = await fetch(url);
			if (response.ok) {
				selectOptions[selectField.field] = await response.json().then((data) =>
					Object.entries(data).map(([key, value]) => ({
						label: value,
						value: selectField.valueType === 'number' ? parseInt(key) : key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
		}
	}

	generalSettingModel.selectOptions = selectOptions;

	const ssoForm = await superValidate(ssoSettings, zod(SSOSettingsSchema), { errors: false });
	const generalSettingForm = await superValidate(generalSettings, zod(GeneralSettingsSchema), {
		errors: false
	});
	const featureFlagForm = await superValidate(featureFlagSettings, zod(FeatureFlagsSchema), {
		errors: false
	});

	return {
		ssoSettings,
		ssoForm,
		ssoModel,
		generalSettings,
		generalSettingForm,
		generalSettingModel,
		featureFlagSettings,
		featureFlagForm,
		featureFlagModel,
		title: m.settings()
	};
};

export const actions: Actions = {
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
			method: 'PATCH',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash({ type: 'success', message: m.ssoSettingsupdated() }, event);

		return { form };
	},
	general: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		// Extract conversion_rate before validation (it's not in the schema)
		const conversionRate = formData.get('conversion_rate');

		const schema = GeneralSettingsSchema;
		const form = await superValidate(formData, zod(schema));
		const endpoint = `${BASE_API_URL}/settings/general/`;

		// Prepare request body with conversion_rate if it exists
		const requestBody: any = {
			value: form.data
		};

		if (conversionRate && conversionRate !== '1.0') {
			const parsedRate = parseFloat(conversionRate.toString());
			requestBody.conversion_rate = parsedRate;
		}

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(requestBody)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash({ type: 'success', message: m.generalSettingsUpdated() }, event);

		return { form };
	},
	featureFlags: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = FeatureFlagsSchema;
		const form = await superValidate(formData, zod(schema));
		const endpoint = `${BASE_API_URL}/settings/feature-flags/`;

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash({ type: 'success', message: m.featureFlagSettingsUpdated() }, event);

		return { form };
	},
	generateSamlKeys: async (event) => {
		const response = await event.fetch(`${BASE_API_URL}/accounts/saml/0/generate-keys/`, {
			method: 'POST'
		});

		if (!response.ok) return fail(500, { error: 'Generation failed' });

		const { cert } = await response.json();

		setFlash({ type: 'success', message: m.samlKeysGenerated() }, event);

		return { generatedKeys: { cert } };
	}
};
