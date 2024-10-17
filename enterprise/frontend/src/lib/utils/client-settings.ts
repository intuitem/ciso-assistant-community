import { z } from 'zod';

export const ClientSettingsSchema = z.object({
	id: z.string().uuid(),
	name: z.string().optional().nullable().default(''),
	logo: z.any().optional().nullable(),
	favicon: z.any().optional().nullable(),
  show_images_unauthenticated: z.boolean().default(true),
});
