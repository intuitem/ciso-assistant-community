import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Streams one answer attachment back to the browser. The reviewer surface is tried
// first and the requester's own is the fallback, exactly as the page itself does:
// someone who filed a request holds no folder rights on it.
export const GET: RequestHandler = async ({ fetch, params, locals }) => {
	// +server.ts handlers do not run the parent layout's load, so this route carries its
	// own session check rather than inheriting one.
	if (!locals.user) error(401, 'Unauthorized');

	const paths = [
		`${BASE_API_URL}/quick-form-responses/${params.id}/attachments/${params.attachmentId}/download/`,
		`${BASE_API_URL}/my-requests/${params.id}/attachments/${params.attachmentId}/download/`
	];
	for (const path of paths) {
		const res = await fetch(path);
		if (res.ok) {
			// Pass the body through untouched; only the headers that describe it travel.
			// Forwarded verbatim, including the headers that stop an uploaded file from
			// executing in this origin — dropping them here would undo the backend's work.
			const headers = new Headers();
			for (const h of [
				'content-type',
				'content-disposition',
				'content-length',
				'x-content-type-options',
				'content-security-policy',
				'referrer-policy'
			]) {
				const value = res.headers.get(h);
				if (value) headers.set(h, value);
			}
			return new Response(res.body, { headers });
		}
		if (res.status !== 403 && res.status !== 404) error(res.status, 'Attachment unavailable');
	}
	error(404, 'Attachment not found');
};
