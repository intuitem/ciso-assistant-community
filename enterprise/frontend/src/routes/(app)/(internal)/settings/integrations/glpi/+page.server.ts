import { z } from 'zod';
import { fail } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms/server';
import { setFlash } from 'sveltekit-flash-message/server';
import type { Actions, PageServerLoad } from './$types';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { m } from '#paraglide/messages.js';

const schema = z
	.object({
		id: z.string(),
		provider_id: z.string(),
		folder_id: z.string(),
		is_active: z.boolean().default(true),
		webhook_secret: z.string().optional(),
		credentials: z.object({
			instance_url: z.string().url(),
			client_id: z.string(),
			client_secret: z.string().optional(),
			username: z.string(),
			password: z.string().optional()
		}),
		settings: z.object({
			enable_outgoing_sync: z.boolean().default(false),
			enable_incoming_sync: z.boolean().default(false),
			// Required for sync to function, but unsettable until the integration
			// row exists (the table picker only renders once the config has an id).
			// Enforced via superRefine below for updates.
			table_name: z.string().optional(),
			field_map: z.record(z.string(), z.any()).default({}).optional(),
			value_map: z.record(z.string(), z.any()).default({}).optional()
		})
	})
	.superRefine((data, ctx) => {
		if (data.id && !data.settings.table_name) {
			ctx.addIssue({
				code: z.ZodIssueCode.custom,
				path: ['settings', 'table_name'],
				message: 'A target table must be selected'
			});
		}
	});

export const load: PageServerLoad = async ({ fetch, locals }) => {
	const response = await fetch(`${BASE_API_URL}/integrations/configs/?provider__name=glpi`);
	let config: Record<string, any> = {};
	if (response.ok) {
		config = await response.json().then((res) => res.results[0]);
	}
	if (!config) {
		const providerResponse = await fetch(`${BASE_API_URL}/integrations/providers/?name=glpi`);
		if (!providerResponse.ok) {
			throw new Error('Failed to fetch GLPI provider information');
		}
		const providerData = await providerResponse.json();
		const provider = providerData.results[0];
		config = {
			folder_id: (await locals.getUser())?.root_folder_id,
			provider_id: provider.id
		};
	}

	const form = await superValidate(config, zod(schema), { errors: false });
	return {
		form,
		config,
		provider: 'glpi',
		schema: JSON.stringify(schema),
		title: m.glpiIntegrationConfig()
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
			// Surface DRF's validation detail so the user can see *what* was
			// rejected rather than just "save failed".
			const rawBody = await response.text();
			let detail = '';
			try {
				const parsed = JSON.parse(rawBody);
				detail =
					typeof parsed === 'string'
						? parsed
						: parsed.detail || parsed.error || JSON.stringify(parsed);
			} catch {
				detail = rawBody.slice(0, 200);
			}
			console.error('Failed to save GLPI integration config:', detail);
			setFlash(
				{ type: 'error', message: `Failed to save GLPI integration config: ${detail}` },
				event
			);
			return fail(400, { form: form });
		}
		// Backfill the saved row's id so the form switches to PATCH mode on subsequent
		// saves without waiting for the invalidateAll-triggered reload to settle.
		const saved = await response.json();
		form.data.id = saved.id;
		setFlash({ type: 'success', message: 'Successfully saved GLPI integration config' }, event);
		return { form };
	}
};
