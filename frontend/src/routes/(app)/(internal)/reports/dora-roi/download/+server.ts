import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/entities/generate_dora_roi/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error generating DORA ROI file');
	}

	// Extract filename from Content-Disposition header if available
	const contentDisposition = res.headers.get('Content-Disposition');
	const fileName = contentDisposition
		? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
		: `DORA_ROI_${new Date().toISOString().split('T')[0]}.zip`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/zip',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
