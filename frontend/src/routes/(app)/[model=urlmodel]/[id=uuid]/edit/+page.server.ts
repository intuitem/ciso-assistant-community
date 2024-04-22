import { BASE_API_URL } from '$lib/utils/constants';
import { modelSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setError, superValidate } from 'sveltekit-superforms/server';
import { setFlash } from 'sveltekit-flash-message/server';
import { urlParamModelVerboseName } from '$lib/utils/crud';
import { redirect } from '@sveltejs/kit';

import { localItems, toCamelCase } from '$lib/utils/locales';
import * as m from '$paraglide/messages';
import { languageTag } from '$paraglide/runtime';

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const schema = modelSchema(event.params.model!);
		const endpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/`;
		const form = await superValidate(formData, schema);

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		// NOTE: shape is accessed through schema._def.schema.shape if refined
		const shape = schema.shape || (schema as any)._def.schema.shape;

		const requestInitOptions: RequestInit = {
			method: shape.attachment ? 'PATCH' : 'PUT',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			if (response.error) {
				setFlash({ type: 'error', message: response.error }, event);
				return fail(403, { form: form });
			}
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, value);
			});
			return fail(400, { form: form });
		}
		const createdObject = await res.json();

		if (formData.has('attachment') && (formData.get('attachment') as File).size > 0) {
			const { attachment } = Object.fromEntries(formData) as { attachment: File };
			const attachmentEndpoint = `${BASE_API_URL}/${event.params.model}/${createdObject.id}/upload/`;
			const attachmentRequestInitOptions: RequestInit = {
				headers: {
					'Content-Disposition': `attachment; filename=${encodeURIComponent(attachment.name)}`
				},
				method: 'POST',
				body: attachment
			};
			const attachmentRes = await event.fetch(attachmentEndpoint, attachmentRequestInitOptions);
			if (!attachmentRes.ok) {
				const response = await attachmentRes.json();
				console.error(response);
				if (response.non_field_errors) {
					setError(form, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form });
			}
		}

		const model: string = urlParamModelVerboseName(event.params.model!);
		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({
					object: localItems(languageTag())[toCamelCase(model.toLowerCase())].toLowerCase(),
					name: form.data.name
				})
			},
			event
		);
		redirect(
			302,
			event.url.searchParams.get('next') ?? `/${event.params.model}/${event.params.id}`
		);
	}
};
