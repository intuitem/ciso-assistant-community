import { z } from 'zod';
import type { ZodSchema } from '$lib/utils/schemas';

export const mfaAuthenticateSchema: ZodSchema = z.object({
	code: z
		.string()
		.regex(/^\d{6,8}$/)
		.min(6)
		.max(8) // Recovery codes are 8 digits long
});
