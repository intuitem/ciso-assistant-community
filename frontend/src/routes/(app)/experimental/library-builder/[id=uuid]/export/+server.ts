import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

/**
 * YAML download for a library draft. Deliberately a page-less subroute: a
 * route that also has a +page serves HTML to browser navigations, so an
 * anchor could never reach an `?action=export` endpoint branch there. Here
 * the anchor falls through to a real navigation and the attachment
 * response downloads without leaving the current page.
 */
export const GET: RequestHandler = async ({ params, fetch }) => {
	const r = await fetch(`${BASE_API_URL}/library-drafts/${params.id}/export/`);
	if (!r.ok) {
		// Without this gate the attachment headers below would make the
		// browser download the error body as a .yaml file.
		return new Response(await r.text(), {
			status: r.status,
			headers: { 'Content-Type': r.headers.get('Content-Type') ?? 'application/json' }
		});
	}
	return new Response(await r.blob(), {
		status: r.status,
		headers: {
			'Content-Type': r.headers.get('Content-Type') ?? 'application/yaml',
			'Content-Disposition': r.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
