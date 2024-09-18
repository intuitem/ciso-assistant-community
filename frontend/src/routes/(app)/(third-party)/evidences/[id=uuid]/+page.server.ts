import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { z } from 'zod';
import { setError, superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import type { PageServerLoad } from './$types';
import type { urlModel } from '$lib/utils/types';
import { listViewFields } from '$lib/utils/table';
import { tableSourceMapper, type TableSource } from '@skeletonlabs/skeleton';
import * as m from '$paraglide/messages';
import { zod } from 'sveltekit-superforms/adapters';

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

	return { URLModel, evidence, object, tables, deleteForm };
};

export const actions: Actions = {
	deleteAttachment: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const deleteAttachmentForm = await superValidate(formData, zod(schema));

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
			setFlash({ type: 'error', message: m.anErrorOccurred() }, event);
			return fail(400, { form: deleteAttachmentForm });
		}
		setFlash({ type: 'success', message: m.attachmentDeleted() }, event);
		throw redirect(302, `/${urlmodel}/${id}`);
	}
};
