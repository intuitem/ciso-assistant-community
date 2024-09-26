import { z } from 'zod';

export const ClientSettingsSchema = z.object({
	id: z.string().uuid(),
	name: z.string().optional().nullable(),
	logo: z.any().optional().nullable(),
	favicon: z.any().optional().nullable()
});
