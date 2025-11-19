import { BASE_API_URL } from '$lib/utils/constants';
import { safeTranslate } from '$lib/utils/i18n';
import { webhookEndpointSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { redirect } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { fail, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/webhooks/endpoints/${event.params.id}/`;
	const response = await event.fetch(endpoint);

	if (!response.ok) {
		console.error('Failed to fetch webhook endpoint:', await response.text());
		redirect(302, '/settings');
	}

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
				return fail(res.status, { form });
			}
		}

		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.webhookEndpoint() })
			},
			event
		);

		redirect(302, '/settings');
	}
};
