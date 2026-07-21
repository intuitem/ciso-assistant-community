import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

/**
 * The standalone framework editor collapsed onto the library builder
 * (/experimental/library-builder). This route only keeps the image-serving
 * contract alive: node descriptions authored with the editor embed
 * `/frameworks/{id}/builder?_action=serve-image&attachment_id=…` URLs
 * (see MarkdownRenderer's INTERNAL_IMG_RE), which must keep resolving
 * wherever those descriptions are rendered.
 */
export const GET: RequestHandler = async ({ fetch, url, params }) => {
	if (url.searchParams.get('_action') !== 'serve-image') {
		return new Response(null, { status: 404 });
	}
	const attachmentId = url.searchParams.get('attachment_id');
	if (!attachmentId) {
		return new Response(JSON.stringify({ error: 'attachment_id required' }), {
			status: 400
		});
	}
	// attachmentId is interpolated into the proxied URL path: constrain it to
	// a UUID so crafted values (e.g. ../ segments) can't retarget the proxy.
	if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(attachmentId)) {
		return new Response(JSON.stringify({ error: 'invalid attachment_id' }), {
			status: 400
		});
	}
	const apiUrl = `${BASE_API_URL}/frameworks/${params.id}/serve-image/${attachmentId}/`;
	const res = await fetch(apiUrl);
	if (!res.ok) {
		return new Response(null, { status: res.status });
	}
	const contentType = res.headers.get('Content-Type') || 'application/octet-stream';
	const body = await res.arrayBuffer();
	return new Response(body, {
		status: 200,
		headers: { 'Content-Type': contentType }
	});
};
