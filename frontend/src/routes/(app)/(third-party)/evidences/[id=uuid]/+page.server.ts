import { handleErrorResponse } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import * as m from '$paraglide/messages';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const URLModel = 'evidences';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const evidence = await res.json();

	const object = await fetch(`${endpoint}object/`).then((res) => res.json());

	const tables: Record<string, any> = {};

	for (const key of ['applied-controls', 'requirement-assessments'] as urlModel[]) {
		const keyEndpoint = `${BASE_API_URL}/${key}/?evidences=${params.id}`;
		const response = await fetch(keyEndpoint);
		if (response.ok) {
			const data = await response.json().then((data) => data.results);
			const bodyData = tableSourceMapper(data, listViewFields[key].body);

			const table: TableSource = {
				head: listViewFields[key].head,
				body: bodyData,
				meta: data
			};
			tables[key] = table;
		} else {
			console.error(`Failed to fetch data for ${key}: ${response.statusText}`);
		}
	}

	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));

	const attachmentDeleteSchema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
	const attachmentDeleteForm = await superValidate(
		{
			urlmodel: URLModel,
			id: params.id
		},
		zod(attachmentDeleteSchema)
	);

	return { URLModel, evidence, object, tables, deleteForm, attachmentDeleteForm };
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
