import { z } from 'zod';
import { superValidate } from 'sveltekit-superforms/server';
import type { Actions, PageServerLoad } from './$types';
import { zod } from 'sveltekit-superforms/adapters';
import { redirect } from '@sveltejs/kit';
import { BASE_API_URL } from '$lib/utils/constants';

const schema = z.object({
	provider_id: z.string(),
	folder_id: z.string(),
	is_active: z.boolean().default(true),
	credentials: z.object({
		server_url: z.string().url(),
		email: z.string().email(),
		api_token: z.string()
	}),
	settings: z.object({
		project_key: z.string(),
		issue_type: z.string().default('Task')
	})
});

export const load: PageServerLoad = async ({ fetch }) => {
	const response = await fetch(`${BASE_API_URL}/integrations/configs/`);
	let config = {};
	if (response.ok) {
		config = await response.json().then((res) => res.results[0]);
	}
	const form = await superValidate(config, zod(schema));
	return { form, config, schema: JSON.stringify(schema) };
};

export const actions: Actions = {
	save: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(schema));
		if (!form.valid) {
			return { form };
		}

		const { id, ...data } = form.data;

		const body = {
			...data
		};

		const response = id
			? await fetch(`${BASE_API_URL}/integrations/configs/${id}/`, {
					method: 'PATCH',
					body: JSON.stringify(body)
				})
			: await fetch(`${BASE_API_URL}/integrations/configs/`, {
					method: 'POST',
					body: JSON.stringify(body)
				});

		if (!response.ok) {
			console.error('Failed to save Jira integration config:', await response.text());
		}
		return { form };
	}
};
