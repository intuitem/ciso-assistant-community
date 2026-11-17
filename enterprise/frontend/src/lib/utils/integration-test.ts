import { safeTranslate } from '#lib/utils/i18n.js';
import { m } from '#paraglide/messages.js';

const firstString = (...values: unknown[]) =>
	values.flat().find((v): v is string => typeof v === 'string');

/**
 * Turn a failed response of the integrations test-connection proxy into a
 * short, localized reason to show next to "connection failed".
 *
 * The proxy forwards backend error bodies as a JSON-encoded string. Field
 * errors carry frontend message keys; provider schema errors are plain text
 * from the backend; status "error" means the request itself blew up (network,
 * URL, SSRF guard). Status "failure" means the provider rejected the
 * credentials, which the generic label already says, so it adds nothing.
 */
export async function describeTestFailure(response: Response): Promise<string> {
	let body: unknown;
	try {
		body = await response.json();
		if (typeof body === 'string') body = JSON.parse(body);
	} catch {
		return '';
	}
	if (!body || typeof body !== 'object') return '';
	const errors = body as Record<string, unknown>;
	const messageKey = firstString(
		errors.credentials,
		errors.configuration_id,
		errors.provider,
		errors.detail
	);
	if (messageKey) return safeTranslate(messageKey);
	const providerError = firstString(errors.provider_specific_errors);
	if (providerError) return providerError;
	if (errors.status === 'error') return m.anErrorOccurred();
	return '';
}
