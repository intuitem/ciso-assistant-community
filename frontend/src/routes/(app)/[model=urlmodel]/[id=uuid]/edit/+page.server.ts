import { BASE_API_URL } from '$lib/utils/constants';
import { modelSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setError, superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import { urlParamModelVerboseName } from '$lib/utils/crud';
import { getSecureRedirect } from '$lib/utils/helpers';
import { redirect } from '@sveltejs/kit';

import { localItems, toCamelCase } from '$lib/utils/locales';
import * as m from '$paraglide/messages';
import { languageTag } from '$paraglide/runtime';
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

		const fileFields = Object.fromEntries(
			Object.entries(form.data).filter(([, value]) => value instanceof File)
		);

		Object.keys(fileFields).forEach((key) => {
			form.data[key] = undefined;
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
				if (file.size <= 0) {
					continue;
				}
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
					object: localItems()[toCamelCase(modelVerboseName.toLowerCase())].toLowerCase()
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
