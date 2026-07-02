import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Endpoint-only route (no +page here) so an <iframe>/<a download> — which send
// Accept: text/html — reach this handler instead of rendering the app page.
export const GET: RequestHandler = async ({ fetch, url }) => {
	const rev = url.searchParams.get('rev');
	if (!rev) error(400, { message: 'Missing rev' });
	const res = await fetch(`${BASE_API_URL}/document-revisions/${rev}/file/`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.text());
	}
	const buffer = await res.arrayBuffer();
	return new Response(buffer, {
		status: 200,
		headers: {
			'Content-Type': res.headers.get('Content-Type') || 'application/octet-stream',
			'Content-Disposition': res.headers.get('Content-Disposition') || 'attachment'
		}
	});
};
