import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, setHeaders, params }) => {
	const endpoint = `${BASE_API_URL}/evidences/${params.id}/attachment/`;

	try {
		const attachmentResponse = await fetch(endpoint);

		if (!attachmentResponse.body) {
			throw new Error('No response body');
		}

		const contentType = attachmentResponse.headers.get('Content-Type');
		if (!contentType) {
			return new Response('No Content-Type header', { status: 400 });
		}

		const contentDisposition = attachmentResponse.headers.get('Content-Disposition');
		if (!contentDisposition) {
			return new Response('No Content-Disposition header', { status: 400 });
		}

		const fileName = contentDisposition?.split('filename=')[1];
		if (!fileName) {
			return new Response('No filename in Content-Disposition header', { status: 400 });
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
			'Content-Disposition': `attachment; filename="${fileName}"`
		});
		return new Response(stream, { status: attachmentResponse.status });
	} catch (err) {
		console.error(err);
		return error(400, 'Error fetching attachment');
	}
};
