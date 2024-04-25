import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { mimeTypes } from '$lib/utils/mimetypes';

export const GET: RequestHandler = async ({ fetch, setHeaders, params }) => {
	const endpoint = `${BASE_API_URL}/evidences/${params.id}/attachment`;

	try {
		const attachmentResponse = await fetch(endpoint);

		if (!attachmentResponse.body) {
			throw new Error('No response body');
		}

		const contentType = attachmentResponse.headers.get('Content-Type');
		if (!contentType) {
			return new Response('No Content-Type header', { status: 400 });
		}

		const fileExtension = mimeTypes[contentType] ? mimeTypes[contentType][0] : 'bin';
		if (!mimeTypes[contentType]) {
			console.warn(`Unknown content type ${contentType}`);
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
