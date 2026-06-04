import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';
import {
	FeatureFlagsSchema,
	GeneralSettingsSchema,
	SSOSettingsSchema,
	VulnerabilitySlaSchema,
	SecIntelFeedsSchema,
	webhookEndpointSchema,
	auditSinkSchema
} from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
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

	const auditSinks = await fetch(`${BASE_API_URL}/webhooks/audit-sinks/`)
		.then((res) => (res.ok ? res.json() : { results: [] }))
		.then((res) => res.results ?? []);

	const selectOptions: Record<string, any> = {};

	const ssoModel = getModelInfo('sso-settings');
	const generalSettingModel = getModelInfo('general-settings');
	const featureFlagModel = getModelInfo('feature-flags');
	const vulnerabilitySlaModel = getModelInfo('vulnerability-sla');
	const secIntelFeedsModel = getModelInfo('sec-intel-feeds');

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

	const vulnerabilitySlaSettings = await fetch(`${BASE_API_URL}/settings/vulnerability-sla/`).then(
		(res) => res.json()
	);
	const secIntelFeedsSettings = await fetch(`${BASE_API_URL}/settings/sec-intel-feeds/`).then(
		(res) => res.json()
	);

	const ssoForm = await superValidate(ssoSettings, zod(SSOSettingsSchema), { errors: false });
	const generalSettingForm = await superValidate(generalSettings, zod(GeneralSettingsSchema), {
		errors: false
	});
	const featureFlagForm = await superValidate(featureFlagSettings, zod(FeatureFlagsSchema), {
		errors: false
	});
	const vulnerabilitySlaForm = await superValidate(
		vulnerabilitySlaSettings,
		zod(VulnerabilitySlaSchema),
		{ errors: false }
	);
	const secIntelFeedsForm = await superValidate(secIntelFeedsSettings, zod(SecIntelFeedsSchema), {
		errors: false
	});
	const webhookEndpointCreateForm = await superValidate(zod(webhookEndpointSchema), {
		errors: false
	});
	const auditSinkCreateForm = await superValidate(zod(auditSinkSchema), {
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
		vulnerabilitySlaSettings,
		vulnerabilitySlaForm,
		vulnerabilitySlaModel,
		secIntelFeedsSettings,
		secIntelFeedsForm,
		secIntelFeedsModel,
		webhookEndpoints,
		webhookEndpointCreateForm,
		auditSinks,
		auditSinkCreateForm,
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
	vulnerabilitySla: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = VulnerabilitySlaSchema;
		const form = await superValidate(formData, zod(schema));
		const endpoint = `${BASE_API_URL}/settings/vulnerability-sla/`;

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash({ type: 'success', message: m.vulnerabilitySlaSettingsUpdated() }, event);

		return { form };
	},
	secIntelFeeds: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = SecIntelFeedsSchema;
		const form = await superValidate(formData, zod(schema));
		const endpoint = `${BASE_API_URL}/settings/sec-intel-feeds/`;

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash({ type: 'success', message: m.secIntelFeedsSettingsUpdated() }, event);

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

		if (!form.valid) {
			return fail(400, { form });
		}

		const endpoint = `${BASE_API_URL}/webhooks/endpoints/`;

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash(
			{ type: 'success', message: m.successfullyCreatedObject({ object: m.webhookEndpoint() }) },
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
	},
	createAuditSink: async (event) => {
		const formData = await event.request.formData();
		if (!formData) {
			return fail(400, { form: null });
		}

		const form = await superValidate(formData, zod(auditSinkSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const data: Record<string, any> = { ...form.data };
		if (typeof data.headers === 'string' && data.headers.trim()) {
			try {
				data.headers = JSON.parse(data.headers);
			} catch {
				return setError(form, 'headers', m.invalidJson());
			}
		} else {
			data.headers = {};
		}

		const endpoint = `${BASE_API_URL}/webhooks/audit-sinks/`;
		const response = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify(data)
		});

		if (!response.ok) return handleErrorResponse({ event, response, form });

		setFlash(
			{ type: 'success', message: m.successfullyCreatedObject({ object: m.auditSink() }) },
			event
		);
		return { form };
	},
	deleteAuditSink: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ id: z.string() });
		const deleteForm = await superValidate(formData, zod(schema));
		const id = deleteForm.data.id;

		if (!deleteForm.valid) {
			return message(deleteForm, { status: 400 });
		}

		const endpoint = `${BASE_API_URL}/webhooks/audit-sinks/${id}/`;
		const res = await event.fetch(endpoint, { method: 'DELETE' });
		if (!res.ok) {
			return message(deleteForm, { status: res.status });
		}
		setFlash(
			{
				type: 'success',
				message: m.successfullyDeletedObject({ object: m.auditSink().toLowerCase() })
			},
			event
		);
		return message(deleteForm, { status: res.status });
	},
	replayAuditSink: async (event) => {
		const formData = await event.request.formData();
		const id = formData.get('id');
		const since = formData.get('since');
		const until = formData.get('until');

		if (!id || !since) {
			setFlash({ type: 'error', message: m.sinceRequiredIso8601() }, event);
			return fail(400, {});
		}

		const body: Record<string, string> = { since: String(since) };
		if (until) body.until = String(until);

		const endpoint = `${BASE_API_URL}/webhooks/audit-sinks/${id}/replay/`;
		const response = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify(body)
		});

		if (!response.ok) {
			const r = await response.json().catch(() => ({}));
			setFlash({ type: 'error', message: safeTranslate(r.error ?? 'replayFailed') }, event);
			return fail(response.status, {});
		}

		const result = await response.json();
		setFlash(
			{
				type: 'success',
				message: m.auditReplayScheduled({ count: result.scheduled ?? 0 })
			},
			event
		);
		return { success: true };
	}
};
