import { z } from 'zod';
import { fail } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms/server';
import { setFlash } from 'sveltekit-flash-message/server';
import type { Actions, PageServerLoad } from './$types';
import { zod } from 'sveltekit-superforms/adapters';
import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';

const schema = z.object({
	id: z.string(),
	provider_id: z.string(),
	folder_id: z.string(),
	is_active: z.boolean().default(true),
	// webhook_secret: z.string().optional(),
	credentials: z.object({
		instance_url: z.string().url(),
		username: z.string(),
		password: z.string().optional()
	}),
	settings: z.object({
		enable_outgoing_sync: z.boolean().default(false),
		enable_incoming_sync: z.boolean().default(false),
		table_name: z.string().default('incident'),
		base_query: z.string().default('active=true')
	})
});

export const load: PageServerLoad = async ({ fetch, locals }) => {
	const response = await fetch(`${BASE_API_URL}/integrations/configs/`);
	let config = {};
	if (response.ok) {
		config = await response.json().then((res) => res.results[0]);
	}
	if (!config) {
		const providerResponse = await fetch(`${BASE_API_URL}/integrations/providers/?name=servicenow`);
		if (!providerResponse.ok) {
			throw new Error('Failed to fetch ServiceNow provider information');
		}
		const providerData = await providerResponse.json();
		const provider = providerData.results[0];
		config = {
			folder_id: locals.user.root_folder_id,
			provider_id: provider.id
		};
	}
	const form = await superValidate(config, zod(schema), { errors: false });
	return {
		form,
		config,
		provider: 'servicenow',
		schema: JSON.stringify(schema),
		title: m.serviceNowIntegrationConfig()
	};
};

export const actions: Actions = {
	save: async (event) => {
		const form = await superValidate(event.request, zod(schema));
		if (!form.valid) {
			return { form };
		}

		const { id, ...data } = form.data;

		const body = {
			...data
		};

		const response = id
			? await event.fetch(`${BASE_API_URL}/integrations/configs/${id}/`, {
					method: 'PATCH',
					body: JSON.stringify(body)
				})
			: await event.fetch(`${BASE_API_URL}/integrations/configs/`, {
					method: 'POST',
					body: JSON.stringify(body)
				});

		if (!response.ok) {
			console.error('Failed to save ServiceNow integration config:', await response.text());
			setFlash({ type: 'error', message: 'Failed to save ServiceNow integration config' }, event);
			return fail(400, { form: form });
		}
		setFlash({ type: 'success', message: 'Successfully savec ServiceNow integration config' }, event);
		return { form };
	}
};
