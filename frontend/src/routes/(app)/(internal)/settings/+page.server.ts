import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';
import {
	FeatureFlagsSchema,
	GeneralSettingsSchema,
	SSOSettingsSchema,
	webhookEndpointSchema
} from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const ssoSettings = await fetch(`${BASE_API_URL}/settings/sso/object/`).then((res) => res.json());
	const generalSettings = await fetch(`${BASE_API_URL}/settings/general/object/`).then((res) =>
		res.json()
	);
	const featureFlagSettings = await fetch(`${BASE_API_URL}/settings/feature-flags/`).then((res) =>
		res.json()
	);
	const webhookEndpoints = await fetch(`${BASE_API_URL}/webhooks/endpoints/`)
		.then((res) => res.json())
		.then((res) => res.results);

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
		webhookEndpoints,
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

		// Prepare request body with optional numeric conversion_rate
		const requestBody: any = {
			value: form.data
		};

		if (conversionRate) {
			const n = Number(conversionRate);
			if (Number.isFinite(n) && n > 0 && n !== 1) {
				requestBody.conversion_rate = n;
			}
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
	},
	createWebhookEndpoint: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = webhookEndpointSchema;
		const form = await superValidate(formData, zod(schema));
		const endpoint = `${BASE_API_URL}/webhooks/endpoints/`;

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash(
			{ type: 'success', message: m.successfullyCreatedObject({ object: m.webhookEndpoint }) },
			event
		);

		return { form };
	},
	deleteWebhookEndpoint: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ id: z.string() });
		const deleteForm = await superValidate(formData, zod(schema));
		const id = deleteForm.data.id;
		const endpoint = `${BASE_API_URL}/webhooks/endpoints/${id}/`;

		if (!deleteForm.valid) {
			console.error(deleteForm.errors);
			return message(deleteForm, { status: 400 });
		}

		const requestInitOptions: RequestInit = {
			method: 'DELETE'
		};
		const res = await event.fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.error) {
				const errorMessages = Array.isArray(response.error) ? response.error : [response.error];
				errorMessages.forEach((error) => {
					setFlash({ type: 'error', message: safeTranslate(error) }, event);
				});
				return message(deleteForm, { status: res.status });
			}
			if (response.non_field_errors) {
				setError(deleteForm, 'non_field_errors', response.non_field_errors);
			}
			return message(deleteForm, { status: res.status });
		}
		setFlash(
			{
				type: 'success',
				message: m.successfullyDeletedObject({
					object: m.webhookEndpoint().toLowerCase()
				})
			},
			event
		);

		return message(deleteForm, { status: res.status });
	}
};
