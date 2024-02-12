import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { mimeTypes } from '$lib/utils/mimetypes';

export const GET: RequestHandler = async ({ fetch, setHeaders, params }) => {
	const endpoint = `${BASE_API_URL}/evidences/${params.id}/attachment`;

	try {
		const attachmentResponse = await fetch(endpoint);
		const contentType = attachmentResponse.headers.get('Content-Type');
		const fileExtension = contentType ? mimeTypes[contentType][0] : 'bin';

		if (!attachmentResponse.body) {
			throw new Error('No response body');
		}

		const reader = attachmentResponse.body.getReader();
		const stream = new ReadableStream({
			start(controller) {
				function push() {
					reader.read().then(({ done, value }) => {
						if (done) {
							controller.close();
							return;
						}
						controller.enqueue(value);
						push();
					});
				}
				push();
			}
		});

		setHeaders({
			'Content-Type': contentType ?? 'application/octet-stream',
			'Content-Disposition': `attachment; filename="${params.id}.${fileExtension}"`
		});
		return new Response(stream, { status: attachmentResponse.status });
	} catch (err) {
		console.error(err);
		return error(400, 'Error fetching attachment');
	}
};
