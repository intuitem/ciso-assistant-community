import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';

import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';

import { fail, type Actions, type RequestEvent } from '@sveltejs/kit';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import {
	defaultWriteFormAction,
	nestedDeleteFormAction,
	nestedWriteFormAction,
	handleErrorResponse
} from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';

import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

async function handleRiskAcceptanceTransition(
	event: Pick<RequestEvent, 'request' | 'fetch' | 'params'>,
	transition: 'accept' | 'reject' | 'revoke',
	successMessage: (args: { object: string; id: string }) => string
) {
	const { request, fetch, params } = event;
	const formData = await request.formData();
	const schema =
		params.model === 'risk-acceptances'
			? z.object({
					urlmodel: z.string(),
					id: z.string().uuid(),
					justification: z.string().optional()
				})
			: z.object({ urlmodel: z.string(), id: z.string().uuid() });
	const form = await superValidate(formData, zod(schema));

	const { urlmodel, id, justification } = form.data;
	const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/${transition}/`;

	if (!form.valid) {
		return fail(400, { form });
	}

	const requestInitOptions: RequestInit =
		params.model === 'risk-acceptances'
			? {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ justification })
				}
			: { method: 'POST' };

	const res = await fetch(endpoint, requestInitOptions);
	if (!res.ok) {
		const response = await res.json();
		if (response.non_field_errors) {
			setError(form, 'non_field_errors', response.non_field_errors);
		}
		return fail(400, { form });
	}

	const model: string = urlParamModelVerboseName(params.model!);
	// TODO: reference object by name instead of id
	return message(
		form,
		successMessage({
			object: safeTranslate(model).toLowerCase(),
			id
		})
	);
}

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo(event.params.model);

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	if (event.params.model === 'applied-controls') {
		const appliedControlSchema = modelSchema(event.params.model + '_duplicate');
		const appliedControl = data.data;
		const initialDataDuplicate = {
			name: appliedControl.name,
			description: appliedControl.description,
			folder: appliedControl.folder.id
		};

		const appliedControlDuplicateForm = await superValidate(
			initialDataDuplicate,
			zod(appliedControlSchema),
			{
				errors: false
			}
		);

		data.duplicateForm = appliedControlDuplicateForm;
	}

	if (event.params.model === 'organisation-objectives') {
		const objectiveSchema = modelSchema(event.params.model);
		const objectEndpoint = `${BASE_API_URL}/organisation-objectives/${event.params.id}/object/`;
		const objectRes = await event.fetch(objectEndpoint);
		if (objectRes.ok) {
			const objectData = await objectRes.json();
			const objectiveDuplicateForm = await superValidate(objectData, zod(objectiveSchema), {
				errors: false
			});
			data.duplicateForm = objectiveDuplicateForm;
		}
	}

	return data;
};

export const actions: Actions = {
	create: async (event) => {
		const redirectToWrittenObject = Boolean(event.params.model === 'perimeters');
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	update: async (event) => {
		return defaultWriteFormAction({
			event,
			urlModel: event.params.model,
			action: 'edit'
		});
	},
	duplicate: async (event) => {
		const formData = await event.request.formData();

		if (!formData) return;

		const schema = modelSchema((event.params.model + '_duplicate') as string);

		const form = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/duplicate/`;

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};
		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		const res = await response.json();
		const newId = res.results?.id;

		const modelVerboseName: string = urlParamModelVerboseName(event.params.model as string);
		setFlash(
			{
				type: 'success',
				message: m.successfullyDuplicateObject({
					object: safeTranslate(modelVerboseName).toLowerCase()
				})
			},
			event
		);

		if (newId) {
			return message(form, { redirect: `/${event.params.model}/${newId}` });
		}

		return { form };
	},
	reject: async ({ request, fetch, params }) => {
		return handleRiskAcceptanceTransition({ request, fetch, params }, 'reject', (args) =>
			m.successfullyRejectedObject(args)
		);
	},
	submit: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const submitForm = await superValidate(formData, zod(schema));

		const urlmodel = submitForm.data.urlmodel;
		const id = submitForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/submit/`;

		if (!submitForm.valid) {
			return fail(400, { form: submitForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(submitForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: submitForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			submitForm,
			m.successfullyValidatedObject({
				object: safeTranslate(model).toLowerCase(),
				id: id
			})
		);
	},

	draft: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const draftForm = await superValidate(formData, zod(schema));

		const urlmodel = draftForm.data.urlmodel;
		const id = draftForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/draft/`;

		if (!draftForm.valid) {
			return fail(400, { form: draftForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(draftForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: draftForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			draftForm,
			m.successfullyValidatedObject({
				object: safeTranslate(model).toLowerCase(),
				id: id
			})
		);
	},
	accept: async ({ request, fetch, params }) => {
		return handleRiskAcceptanceTransition({ request, fetch, params }, 'accept', (args) =>
			m.successfullyValidatedObject(args)
		);
	},
	revoke: async ({ request, fetch, params }) => {
		return handleRiskAcceptanceTransition({ request, fetch, params }, 'revoke', (args) =>
			m.successfullyRevokedObject(args)
		);
	}
};
