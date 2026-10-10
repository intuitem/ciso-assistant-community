import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Framework-specific exports (the audit's `framework_exports`), such as a
// publisher's official self-assessment template.
export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/compliance-assessments/${params.id}/framework-exports/${encodeURIComponent(params.exportId)}/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status, 'Error fetching the export');
	}

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/octet-stream',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
