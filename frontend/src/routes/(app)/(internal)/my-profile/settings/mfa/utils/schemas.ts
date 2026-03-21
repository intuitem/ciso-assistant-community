import { z } from 'zod';

export const activateTOTPSchema: z.ZodObject<any> = z.object({
	code: z
		.string()
		.regex(/^\d{6}$/)
		.min(6)
		.max(6)
});
