import { z } from 'zod';
import type { AnyZodObject } from '$lib/utils/schemas';

export const activateTOTPSchema: AnyZodObject = z.object({
	code: z
		.string()
		.regex(/^\d{6}$/)
		.min(6)
		.max(6)
});
