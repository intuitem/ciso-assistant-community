import { z, type AnyZodObject } from 'zod';

export const activateTOTPSchema: AnyZodObject = z.object({
	code: z
		.string()
		.regex(/^\d{6}$/)
		.min(6)
		.max(6)
});
