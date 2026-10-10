import { BASE_API_URL } from '$lib/utils/constants';
import { urlParamModelVerboseName } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { fail, message, superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import type { Actions } from '@sveltejs/kit';
import { modelSchema } from '$lib/utils/schemas';
import { handleErrorResponse } from '$lib/utils/actions';

export const actions: Actions = {
	duplicate: async (event) => {
		const formData = await event.request.formData();
		if (!formData) return;

		const schema = modelSchema('applied-controls_duplicate');
		const form = await superValidate(formData, zod(schema));
		const endpoint = `${BASE_API_URL}/applied-controls/${event.params.id}/duplicate/`;

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const response = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify(form.data)
		});

		if (!response.ok) return handleErrorResponse({ event, response, form });

		const res = await response.json();
		const newId = res.results?.id;

		const modelVerboseName: string = urlParamModelVerboseName('applied-controls');
		setFlash(
			{
				type: 'success',
				message: m.successfullyDuplicateObject({
					object: safeTranslate(modelVerboseName).toLowerCase()
				})
			},
			event
		);

		if (newId) {
			return message(form, { redirect: `/applied-controls/${newId}` });
		}

		return { form };
	},
	syncAppliedControls: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = z.object({ id: z.string().uuid() });
		const form = await superValidate(formData, zod(schema));

		const response = await event.fetch(
			`${BASE_API_URL}/applied-controls/${event.params.id}/sync-to-reference-control/?dry_run=false`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			}
		);
		if (response.ok) {
			setFlash(
				{
					type: 'success',
					message: m.syncToAppliedControlsSuccess()
				},
				event
			);
		} else {
			setFlash(
				{
					type: 'error',
					message: m.syncToAppliedControlsError()
				},
				event
			);
		}

		const responseData = await response.json();
		const message = { appliedControlsSync: responseData };

		return { form, message };
	}
};
