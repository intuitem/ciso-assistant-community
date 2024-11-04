import { z, type AnyZodObject } from 'zod';

export const mfaAuthenticateSchema: AnyZodObject = z.object({
	code: z
		.string()
		.regex(/^\d{6,8}$/)
		.min(6)
		.max(8) // Recovery codes are 8 digits long
});
