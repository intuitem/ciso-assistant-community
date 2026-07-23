import { BASE_API_URL } from '$lib/utils/constants';

import type { RequestHandler } from './$types';

// Inbound webhook passthrough (spec D23): the frontend origin is the only
// surface guaranteed reachable in every deployment, so hook deliveries enter
// here and are forwarded to the backend over the internal network. Deployments
// whose reverse proxy routes /api/* straight to the backend never hit this
// route — same URL, short-circuited.
//
// The body is forwarded as RAW bytes: HMAC signatures are computed over the
// raw payload, so parsing/re-serializing would break verification. Cookies are
// never forwarded (the URL secret is the credential). Note that senders must
// use a JSON content type — SvelteKit's cross-origin protection rejects
// form-encoded POSTs before this handler runs, and the backend only maps
// JSON object payloads anyway.

// Hook URLs are Django-style (trailing slash); without this SvelteKit 308s
// the delivery, and not every sender follows redirects with the body intact.
export const trailingSlash = 'always';

const MAX_BODY_BYTES = 1024 * 1024;

const FORWARDED_HEADERS = ['content-type', 'x-hub-signature-256', 'x-signature-256'];

export const POST: RequestHandler = async ({ params, request, getClientAddress }) => {
	const payloadTooLarge = () =>
		new Response(JSON.stringify({ error: 'payloadTooLarge' }), {
			status: 413,
			headers: { 'content-type': 'application/json' }
		});

	const declaredLength = Number(request.headers.get('content-length') ?? '0');
	if (declaredLength > MAX_BODY_BYTES) return payloadTooLarge();
	const body = await request.arrayBuffer();
	if (body.byteLength > MAX_BODY_BYTES) return payloadTooLarge();

	const headers = new Headers();
	for (const name of FORWARDED_HEADERS) {
		const value = request.headers.get(name);
		if (value) headers.set(name, value);
	}
	// Real sender IP for backend-side throttling; append to any upstream chain.
	try {
		const chain = request.headers.get('x-forwarded-for');
		const client = getClientAddress();
		headers.set('x-forwarded-for', chain ? `${chain}, ${client}` : client);
	} catch {
		// getClientAddress is adapter-dependent; the hook works without it.
	}

	const res = await fetch(
		`${BASE_API_URL}/workflows/hooks/${params.workflow_id}/${params.node_ref}/${params.secret}/`,
		{ method: 'POST', headers, body }
	);
	return new Response(await res.arrayBuffer(), {
		status: res.status,
		headers: { 'content-type': res.headers.get('content-type') ?? 'application/json' }
	});
};
