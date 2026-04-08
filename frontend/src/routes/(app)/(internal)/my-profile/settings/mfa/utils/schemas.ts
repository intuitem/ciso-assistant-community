import { z } from 'zod';
import type { ZodSchema } from '$lib/utils/schemas';

export const activateTOTPSchema: ZodSchema = z.object({
	code: z
		.string()
		.regex(/^\d{6}$/)
		.min(6)
		.max(6)
});

export const registerWebAuthnSchema: ZodSchema = z.object({
	name: z.string().max(100),
	credential: z.any()
});
