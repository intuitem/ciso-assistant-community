import { z } from 'zod';

// One schema for the page and its save action, so both apply the same rules.
export const schema = z
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
			// Enforced below for updates.
			table_name: z.string().optional(),
			field_map: z.record(z.string(), z.any()).default({}).optional(),
			value_map: z.record(z.string(), z.any()).default({}).optional()
		})
	})
	.superRefine((data, ctx) => {
		// An inactive configuration can be saved without a target: switching it
		// off must stay possible when the table list cannot be loaded.
		if (data.id && data.is_active && !data.settings.table_name) {
			ctx.addIssue({
				code: z.ZodIssueCode.custom,
				path: ['settings', 'table_name'],
				message: 'A target table must be selected'
			});
		}
		// On creation there is no stored secret to fall back on, and GLPI
		// deliveries are refused without one.
		if (!data.id && data.settings.enable_incoming_sync && !data.webhook_secret) {
			ctx.addIssue({
				code: z.ZodIssueCode.custom,
				path: ['webhook_secret'],
				message: 'A webhook secret is required to enable incoming sync'
			});
		}
	});
