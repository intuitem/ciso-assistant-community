import { BASE_API_URL } from '$lib/utils/constants';
import { zod } from 'sveltekit-superforms/adapters';
import { getModelInfo } from '$lib/utils/crud';
import { fail, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';
import { webhookEndpointSchema } from '$lib/utils/schemas';
import { setFlash } from 'sveltekit-flash-message/server';
import { redirect } from '@sveltejs/kit';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/webhooks/endpoints/${event.params.id}/`;
	const response = await event.fetch(endpoint);
	const webhookEndpoint = await response.json();
	const form = await superValidate(webhookEndpoint, zod(webhookEndpointSchema), { errors: false });

	return { webhookEndpoint, title: webhookEndpoint.name, form };
};

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(webhookEndpointSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const endpoint = `${BASE_API_URL}/webhooks/endpoints/${event.params.id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.text();
			console.error(response);
			if (response.error) {
				setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
			}
			redirect(302, '/login');
		}

		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.webhookEndpoint })
			},
			event
		);

		redirect(302, '/settings');
	}
};
