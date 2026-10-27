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
