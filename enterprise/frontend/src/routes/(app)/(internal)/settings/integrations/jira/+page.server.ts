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
			server_url: z.string().url(),
			email: z.string().email(),
			api_token: z.string().optional()
		}),
		settings: z.object({
			enable_outgoing_sync: z.boolean().default(false),
			enable_incoming_sync: z.boolean().default(false),
			// Required for sync to function, but unsettable until the integration
			// row exists (the table picker only renders once the config has an id).
			// Enforced via superRefine below for updates.
			table_name: z.string().optional(),
			project_key: z.string().optional(),
			issue_type: z.string().optional(),
			field_map: z.record(z.string(), z.any()).default({}).optional(),
			value_map: z.record(z.string(), z.any()).default({}).optional(),
			models: z.record(z.string(), z.any()).default({}).optional()
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

// The page waits for this call, and the backend's Jira client can take 30s+
// with retries when Jira is slow or unreachable.
const RESOLVE_TABLE_TIMEOUT_MS = 5000;

// Configs saved before issue types were referenced by id hold the issue type
// name ("KAN:Tâche"). It matches none of the picker's "<KEY>:<id>" options, so
// the picker would clear the table and its maps: resolve it to its id form
// before the form is built. On failure or timeout the value is kept as is.
async function resolveTableName(
	fetch: typeof globalThis.fetch,
	configId: string,
	modelKey: string,
	tableName: string | undefined
): Promise<string | undefined> {
	const separator = tableName?.indexOf(':') ?? -1;
	if (!tableName || separator === -1 || /^\d+$/.test(tableName.slice(separator + 1))) {
		return tableName;
	}
	try {
		const response = await fetch(`${BASE_API_URL}/integrations/configs/${configId}/rpc/`, {
			method: 'POST',
			body: JSON.stringify({
				action: 'resolve_table',
				params: { table_name: tableName, model_key: modelKey }
			}),
			signal: AbortSignal.timeout(RESOLVE_TABLE_TIMEOUT_MS)
		});
		if (!response.ok) return tableName;
		const data = await response.json();
		return data?.result || tableName;
	} catch {
		return tableName;
	}
}

export const load: PageServerLoad = async ({ fetch, locals }) => {
	const response = await fetch(`${BASE_API_URL}/integrations/configs/?provider__name=jira`);
	let config: Record<string, any> = {};
	if (response.ok) {
		config = await response.json().then((res) => res.results[0]);
	}
	if (!config) {
		const providerResponse = await fetch(`${BASE_API_URL}/integrations/providers/?name=jira`);
		if (!providerResponse.ok) {
			throw new Error('Failed to fetch Jira provider information');
		}
		const providerData = await providerResponse.json();
		const provider = providerData.results[0];
		config = {
			folder_id: (await locals.getUser())?.root_folder_id,
			provider_id: provider.id
		};
	}

	// Synthesize a composite ``table_name`` from the legacy ``project_key`` /
	// ``issue_type`` settings so existing configs preselect the right entry in
	// the FieldMapper table picker without a data migration.
	const settings = config?.settings;
	if (settings && !settings.table_name && settings.project_key) {
		settings.table_name = `${settings.project_key}:${settings.issue_type || 'Task'}`;
	}

	// Seed the nested per-model structure so the asset FieldMapper's form paths
	// (settings.models.asset.*) exist for binding.
	config.settings = config.settings ?? {};
	config.settings.models = config.settings.models ?? {};
	config.settings.models.asset = config.settings.models.asset ?? {
		field_map: {},
		value_map: {}
	};

	if (config.id) {
		// Every settings block a FieldMapper binds its table picker to, with its
		// model key: the top-level one is the applied control mapping.
		const targets: [Record<string, any>, string][] = [
			[config.settings, 'applied_control'],
			...Object.entries(config.settings.models)
				.filter(([, modelSettings]) => modelSettings)
				.map(
					([modelKey, modelSettings]) => [modelSettings, modelKey] as [Record<string, any>, string]
				)
		];
		await Promise.all(
			targets.map(async ([target, modelKey]) => {
				const resolved = await resolveTableName(fetch, config.id, modelKey, target.table_name);
				if (resolved !== target.table_name) target.table_name = resolved;
			})
		);
	}

	const form = await superValidate(config, zod(schema), { errors: false });
	return {
		form,
		config,
		provider: 'jira',
		schema: JSON.stringify(schema),
		title: m.jiraIntegrationConfig()
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
			// rejected (e.g. "duplicate config for provider+folder") rather than
			// just "save failed".
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
			console.error('Failed to save Jira integration config:', detail);
			setFlash(
				{ type: 'error', message: `Failed to save Jira integration config: ${detail}` },
				event
			);
			return fail(400, { form: form });
		}
		// Backfill the saved row's id so the form switches to PATCH mode on subsequent
		// saves without waiting for the invalidateAll-triggered reload to settle.
		const saved = await response.json();
		form.data.id = saved.id;
		setFlash({ type: 'success', message: 'Successfully saved Jira integration config' }, event);
		return { form };
	}
};
