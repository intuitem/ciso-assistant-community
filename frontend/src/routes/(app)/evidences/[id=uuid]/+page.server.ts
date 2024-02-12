import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { z } from 'zod';
import { setError, superValidate } from 'sveltekit-superforms/server';
import { setFlash } from 'sveltekit-flash-message/server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = (async ({ fetch, params }) => {
	const URLModel = 'evidences';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const evidence = await res.json();

	const object = await fetch(`${endpoint}object/`).then((res) => res.json());

	return { URLModel, evidence, object };
})

export const actions: Actions = {
	deleteAttachment: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const deleteAttachmentForm = await superValidate(formData, schema);

		const urlmodel = deleteAttachmentForm.data.urlmodel;
		const id = deleteAttachmentForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/delete_attachment/`;

		if (!deleteAttachmentForm.valid) {
			return fail(400, { form: deleteAttachmentForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await event.fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(deleteAttachmentForm, 'non_field_errors', response.non_field_errors);
			}
			setFlash({ type: "error", message: "An error has occured" }, event);
			return fail(400, { form: deleteAttachmentForm });
		}
		setFlash({ type: "success", message: "Attachment successfully deleted" }, event);
		throw redirect(302, `/${urlmodel}/${id}`)
	}

}