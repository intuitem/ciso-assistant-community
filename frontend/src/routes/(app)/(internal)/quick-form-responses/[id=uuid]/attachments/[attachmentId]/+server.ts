import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Reviewer surface first, requester's own as fallback: a requester holds no folder
// rights on their own request.
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
			// Forwarded verbatim, including the headers that stop the file executing here.
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
