import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';

import * as m from '$paraglide/messages';

import { safeTranslate } from '$lib/utils/i18n';
import { modelSchema } from '$lib/utils/schemas';
import { RequestEvent, fail } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

export async function defaultCreateFormAction(event: RequestEvent, urlModel: string) {
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

	const endpoint = `${BASE_API_URL}/${urlModel}/`;
	const model = getModelInfo(urlModel!);

	const fileFields: Record<string, File> = Object.fromEntries(
		Object.entries(form.data).filter(([key]) => model.fileFields?.includes(key) ?? false)
	);

	Object.keys(fileFields).forEach((key) => {
		form.data[key] = undefined;
	});

	const requestInitOptions: RequestInit = {
		method: 'POST',
		body: JSON.stringify(form.data)
	};

	const res = await event.fetch(endpoint, requestInitOptions);

	if (!res.ok) {
		const response: Record<string, any> = await res.json();
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

	const modelVerboseName: string = urlModel ? urlParamModelVerboseName(urlModel) : '';

	setFlash(
		{
			type: 'success',
			message: m.successfullyCreatedObject({
				object: safeTranslate(modelVerboseName).toLowerCase()
			})
		},
		event
	);

	return { createForm: form };
}
