import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url, locals }) => {
	if (!locals.featureflags?.document_management) error(404, 'Not found');
	const rev = url.searchParams.get('rev');
	if (!rev) error(400, 'Missing revision');
	const res = await fetch(`${BASE_API_URL}/document-revisions/${rev}/export-pdf/`);
	if (!res.ok) error(res.status as 400, 'PDF export failed');
	return new Response(await res.arrayBuffer(), {
		headers: {
			'Content-Type': 'application/pdf',
			'Content-Disposition':
				res.headers.get('content-disposition') ?? 'attachment; filename="document.pdf"'
		}
	});
};
