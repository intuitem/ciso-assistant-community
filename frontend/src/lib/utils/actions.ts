import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';

import * as m from '$paraglide/messages';

import { safeTranslate } from '$lib/utils/i18n';
import { modelSchema } from '$lib/utils/schemas';
import { type RequestEvent, fail, redirect } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { getSecureRedirect } from './helpers';
import { z } from 'zod';

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
	if (action === 'create') {
		return `${BASE_API_URL}/${urlModel}/`;
	}
	const id = event.params.id;
	return `${BASE_API_URL}/${urlModel}/${id}/`;
}

export async function defaultWriteFormAction({
	event,
	urlModel,
	action,
	doRedirect = true
}: {
	event: RequestEvent;
	urlModel: string;
	action: FormAction;
	doRedirect?: boolean;
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

	const fileFields: Record<string, File> = Object.fromEntries(
		Object.entries(form.data).filter(([key]) => model.fileFields?.includes(key) ?? false)
	);

	Object.keys(fileFields).forEach((key) => {
		form.data[key] = undefined;
	});

	const requestInitOptions: RequestInit = {
		method: getHTTPMethod({ action, fileFields }),
		body: JSON.stringify(form.data)
	};

	const res = await event.fetch(endpoint, requestInitOptions);

	if (!res.ok) {
		const response: Record<string, string> = await res.json();
		console.error(response);
		if (response.warning) {
			setFlash({ type: 'warning', message: response.warning }, event);
			return { createForm: form };
		}
		if (response.error) {
			setFlash({ type: 'error', message: response.error }, event);
			return { createForm: form };
		}
		Object.entries(response).forEach(([key, value]) => {
			setError(form, key, value);
		});
		return fail(400, { form: form });
	}

	const createdObject = await res.json();

	if (fileFields) {
		for (const [, file] of Object.entries(fileFields)) {
			if (!file) continue;
			if (file.size <= 0) continue;
			const fileUploadEndpoint = `${BASE_API_URL}/${urlModel}/${createdObject.id}/upload/`;
			const fileUploadRequestInitOptions: RequestInit = {
				headers: {
					'Content-Disposition': `attachment; filename=${encodeURIComponent(file.name)}`
				},
				method: 'POST',
				body: file
			};
			const fileUploadRes = await event.fetch(fileUploadEndpoint, fileUploadRequestInitOptions);
			if (!fileUploadRes.ok) {
				const response = await fileUploadRes.json();
				console.error(response);
				if (response.non_field_errors) {
					setError(form, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form: form });
			}
		}
	}

	setFlash(
		{
			type: 'success',
			message: getSuccessMessage({ urlModel, action }) as string
		},
		event
	);

	const next = getSecureRedirect(event.url.searchParams.get('next'));
	if (next && doRedirect) redirect(302, next);

	return { createForm: form };
}

export async function nestedWriteFormAction({
	event,
	action
}: {
	event: RequestEvent;
	action: FormAction;
}) {
	const request = event.request.clone();
	const formData = await request.formData();
	const urlModel = formData.get('urlmodel') as string;
	return defaultWriteFormAction({ event, urlModel, action, doRedirect: false });
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

	const id = deleteForm.data.id;
	const endpoint = `${BASE_API_URL}/${urlModel}/${id}/`;

	if (!deleteForm.valid) {
		console.log(deleteForm.errors);
		return fail(400, { form: deleteForm });
	}

	if (formData.has('delete')) {
		const requestInitOptions: RequestInit = {
			method: 'DELETE'
		};
		const res = await event.fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			console.log(response);
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
