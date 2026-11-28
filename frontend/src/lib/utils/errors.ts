import { error } from '@sveltejs/kit';

/**
 * error() for a backend error body, keeping its fields (detail, error, ...) for the client.
 * Splits out `message` the way Kit's deprecated error(status, body) form did.
 */
export function errorFromBody(status: number, body: unknown): never {
	if (body == null || typeof body !== 'object') {
		error(status, typeof body === 'string' ? body : undefined);
	}
	const { message, ...properties } = body as Record<string, unknown>;
	error(status, typeof message === 'string' ? message : `Error: ${status}`, properties);
}

/**
 * The reason a backend error body gives: its first field error, else its message.
 * Field errors come first because `errorFromBody` always fills `message`, with a
 * generic `Error: <status>` when the backend sent none.
 */
export function getErrorReason(body: unknown): string | undefined {
	if (body == null || typeof body !== 'object') return undefined;
	const { message, ...fields } = body as Record<string, unknown>;
	const fieldError = Object.values(fields).find(Array.isArray)?.[0];
	if (typeof fieldError === 'string' && fieldError) return fieldError;
	return typeof message === 'string' && message ? message : undefined;
}
