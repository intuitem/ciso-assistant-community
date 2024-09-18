import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';
import { getSecureRedirect } from '$lib/utils/helpers';
import { safeTranslate } from '$lib/utils/i18n';
import { modelSchema } from '$lib/utils/schemas';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';

import * as m from '$paraglide/messages';
import { zod } from 'sveltekit-superforms/adapters';

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = modelSchema(event.params.model!);
		const form = await superValidate(formData, zod(schema));

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const endpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/`;

		const model = getModelInfo(event.params.model!);

		const fileFields: Record<string, File> = Object.fromEntries(
			Object.entries(form.data).filter(([key]) => model.fileFields?.includes(key) ?? false)
		);

		Object.keys(fileFields).forEach((key) => {
			delete form.data[key];
		});

		const requestInitOptions: RequestInit = {
			method: fileFields.length > 0 ? 'PATCH' : 'PUT',
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
			return fail(400, { form: form });
		}

		const createdObject = await res.json();

		if (fileFields) {
			for (const [, file] of Object.entries(fileFields)) {
				if (!file) continue;
				if (file.size <= 0) continue;
				const fileUploadEndpoint = `${BASE_API_URL}/${event.params.model}/${createdObject.id}/upload/`;
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

		const modelVerboseName: string = urlParamModelVerboseName(event.params.model!);
		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({
					object: safeTranslate(modelVerboseName).toLowerCase()
				})
			},
			event
		);
		redirect(
			302,
			getSecureRedirect(event.url.searchParams.get('next')) ??
				`/${event.params.model}/${event.params.id}`
		);
	}
};
