import { z } from 'zod';

export const mfaAuthenticateSchema: z.ZodObject<any> = z.object({
	code: z
		.string()
		.regex(/^\d{6,8}$/)
		.min(6)
		.max(8) // Recovery codes are 8 digits long
});
