import { BASE_API_URL } from '#lib/utils/constants.js';

import type { RequestHandler } from './$types';

// Single-use evidence upload passthrough: the remote MCP tool hands out
// <origin>/api/evidences/upload/<token>/ and the claude.ai sandbox curls the
// file here; the frontend origin is the only surface reachable in every
// deployment. Deployments whose reverse proxy routes /api/* straight to the
// backend never hit this route — same URL, short-circuited.
//
// The token in the URL is the credential: cookies are never forwarded. The
// body is STREAMED to the backend, never buffered here; the backend enforces
// ATTACHMENT_MAX_SIZE_MB (Content-Length first, then while reading). Senders
// must use a non-form content type (application/octet-stream): SvelteKit's
// cross-origin protection rejects form-encoded POSTs before this handler runs.

// Django-style URL (trailing slash); without this SvelteKit 308s the upload,
// and curl does not resend the body on a redirect.
export const trailingSlash = 'always';

const FORWARDED_HEADERS = ['content-type', 'content-length'];

export const POST: RequestHandler = async ({ params, request, getClientAddress }) => {
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
		// getClientAddress is adapter-dependent; the upload works without it.
	}

	// Route params arrive decoded, so %2F is a real separator here: encode or a
	// crafted token escapes this path and reaches any backend endpoint.
	let res: Response;
	try {
		res = await fetch(`${BASE_API_URL}/evidences/upload/${encodeURIComponent(params.token)}/`, {
			method: 'POST',
			headers,
			body: request.body,
			// Required by Node's fetch to send a ReadableStream body.
			duplex: 'half'
		} as RequestInit & { duplex: 'half' });
	} catch {
		// Backend unreachable or the stream broke: a JSON answer curl can show.
		return new Response(JSON.stringify({ detail: 'Upload failed: the server is unavailable.' }), {
			status: 502,
			headers: { 'content-type': 'application/json' }
		});
	}
	const responseHeaders = new Headers({
		'content-type': res.headers.get('content-type') ?? 'application/json'
	});
	const retryAfter = res.headers.get('retry-after');
	if (retryAfter) responseHeaders.set('retry-after', retryAfter);
	return new Response(res.body, { status: res.status, headers: responseHeaders });
};
