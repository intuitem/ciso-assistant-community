import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { m } from '$paraglide/messages';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	return await loadDetail({ event, model: getModelInfo('evidences'), id: event.params.id });
};

export const actions: Actions = {
	deleteAttachment: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const form = await superValidate(formData, zod(schema));

		const urlmodel = form.data.urlmodel;
		const id = form.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/delete_attachment/`;

		if (!form.valid) {
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};

		const response = await event.fetch(endpoint, requestInitOptions);
		if (!response.ok) return handleErrorResponse({ event, response, form });
		setFlash({ type: 'success', message: m.attachmentDeleted() }, event);
		return redirect(302, `/${urlmodel}/${id}`);
	}
};
