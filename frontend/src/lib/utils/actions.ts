import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';

import * as m from '$paraglide/messages';

import { safeTranslate } from '$lib/utils/i18n';
import { modelSchema } from '$lib/utils/schemas';
import { fail, redirect, type RequestEvent } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate, type SuperValidated } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import { getSecureRedirect } from './helpers';

type FormAction = 'create' | 'edit';

function getHTTPMethod({
	action,
	fileFields
}: {
	action: FormAction;
	fileFields: Record<string, File>;
}) {
	if (action === 'create') return 'POST';
	return Object.keys(fileFields).length > 0 ? 'PATCH' : 'PUT';
}

function getSuccessMessage({ action, urlModel }: { action: FormAction; urlModel: string }) {
	const modelVerboseName: string = urlModel ? urlParamModelVerboseName(urlModel) : '';
	if (action === 'create') {
		return m.successfullyCreatedObject({
			object: safeTranslate(modelVerboseName).toLowerCase()
		});
	}
	if (action === 'edit') {
		return m.successfullyUpdatedObject({
			object: safeTranslate(modelVerboseName).toLowerCase()
		});
	}
}

function getEndpoint({
	action,
	urlModel,
	event
}: {
	action: FormAction;
	urlModel: string;
	event: RequestEvent;
}) {
	const model = getModelInfo(urlModel);
	if (action === 'create') {
		return model.endpointUrl
			? `${BASE_API_URL}/${model.endpointUrl}/`
			: `${BASE_API_URL}/${urlModel}/`;
	}
	const id = event.params.id;
	return model.endpointUrl
		? `${BASE_API_URL}/${model.endpointUrl}/${id}/`
		: `${BASE_API_URL}/${urlModel}/${id}/`;
}

export async function handleErrorResponse({
	event,
	response,
	form
}: {
	event: RequestEvent;
	response: Response;
	form: SuperValidated;
}) {
	const res: Record<string, string> = await response.json();
	console.error(res);
	if (res.label) {
		res['filtering_labels'] = res.label;
	}
	if (res.warning) {
		setFlash({ type: 'warning', message: safeTranslate(res.warning) }, event);
		return { form };
	}
	if (res.error) {
		setFlash({ type: 'error', message: safeTranslate(res.error) }, event);
		return { form };
	}
	Object.entries(res).forEach(([key, value]) => {
		setError(form, key, safeTranslate(value));
	});
	return fail(400, { form });
}

export async function defaultWriteFormAction({
	event,
	urlModel,
	action,
	doRedirect = true,
	redirectToWrittenObject = false
}: {
	event: RequestEvent;
	urlModel: string;
	action: FormAction;
	doRedirect?: boolean;
	redirectToWrittenObject?: boolean;
}) {
	const formData = await event.request.formData();
	if (!formData) {
		return fail(400, { form: null });
	}

	const schema = modelSchema(urlModel!);
	const form = await superValidate(formData, zod(schema));

	if (!form.valid) {
		console.error(form.errors);
		return fail(400, { form: form });
	}

	const endpoint = getEndpoint({ action, urlModel, event });
	const model = getModelInfo(urlModel!);

	const fileFields = Object.fromEntries(
		Object.entries(form.data).filter(([key]) => model.fileFields?.includes(key) ?? false)
	) as Record<string, File>;

	Object.keys(fileFields).forEach((key) => {
		form.data[key] = undefined;
	});

	const requestInitOptions: RequestInit = {
		method: getHTTPMethod({ action, fileFields }),
		body: JSON.stringify(form.data)
	};

	const res = await event.fetch(endpoint, requestInitOptions);

	if (!res.ok) return await handleErrorResponse({ event, response: res, form });

	const writtenObject = await res.json();

	if (fileFields) {
		for (const [, file] of Object.entries(fileFields)) {
			if (!file) continue;
			if (file.size <= 0) continue;
			const fileUploadEndpoint = `${BASE_API_URL}/${urlModel}/${writtenObject.id}/upload/`;
			const fileUploadRequestInitOptions: RequestInit = {
				headers: {
					'Content-Disposition': `attachment; filename=${encodeURIComponent(file.name)}`
				},
				method: 'POST',
				body: file
			};
			const fileUploadRes = await event.fetch(fileUploadEndpoint, fileUploadRequestInitOptions);
			if (!fileUploadRes.ok) return handleErrorResponse({ event, response: fileUploadRes, form });
		}
	}

	let flashParams = {
		type: 'success',
		message: getSuccessMessage({ urlModel, action }) as string
	};

	if (urlModel == 'users') {
		(flashParams.type = 'warning'), (flashParams.message += safeTranslate('userHasNoRights'));
	}
	setFlash(flashParams, event);

	const next = getSecureRedirect(event.url.searchParams.get('next'));
	if (next && doRedirect) redirect(302, next);

	if (redirectToWrittenObject) {
		return { form, redirect: `/${urlModel}/${writtenObject.id}` };
	}
	return { form };
}

export async function nestedWriteFormAction({
	event,
	action,
	redirectToWrittenObject = false
}: {
	event: RequestEvent;

	action: FormAction;
	redirectToWrittenObject: boolean;
}) {
	const request = event.request.clone();
	const formData = await request.formData();
	const urlModel = formData.get('urlmodel') as string;
	return defaultWriteFormAction({
		event,
		urlModel,
		action,
		doRedirect: false,
		redirectToWrittenObject
	});
}

export async function defaultDeleteFormAction({
	event,
	urlModel
}: {
	event: RequestEvent;
	urlModel: string;
}) {
	const formData = await event.request.formData();
	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(formData, zod(schema));
	const model = getModelInfo(urlModel);

	const id = deleteForm.data.id;
	const endpoint = model.endpointUrl
		? `${BASE_API_URL}/${model.endpointUrl}/${id}/`
		: `${BASE_API_URL}/${model.urlModel}/${id}/`;

	if (!deleteForm.valid) {
		console.error(deleteForm.errors);
		return fail(400, { form: deleteForm });
	}

	if (formData.has('delete')) {
		const requestInitOptions: RequestInit = {
			method: 'DELETE'
		};
		const res = await event.fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.error) {
				setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
				return fail(403, { form: deleteForm });
			}
			if (response.non_field_errors) {
				setError(deleteForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: deleteForm });
		}
		const model: string = urlParamModelVerboseName(urlModel!);
		setFlash(
			{
				type: 'success',
				message: m.successfullyDeletedObject({
					object: safeTranslate(model).toLowerCase()
				})
			},
			event
		);
	}

	return { deleteForm };
}

export async function nestedDeleteFormAction({ event }: { event: RequestEvent }) {
	const request = event.request.clone();
	const formData = await request.formData();
	const urlModel = formData.get('urlmodel') as string;
	return defaultDeleteFormAction({ event, urlModel });
}
