import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/** Proxy a JSON request to the backend API, returning the response as-is. */
async function proxyFetch(
	fetch: typeof globalThis.fetch,
	url: string,
	method: string,
	payload?: unknown
) {
	const res = await fetch(url, {
		method,
		headers: { 'Content-Type': 'application/json' },
		...(payload !== undefined ? { body: JSON.stringify(payload) } : {})
	});

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	if (res.status === 204) {
		return new Response(null, { status: 204 });
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
}

function entityUrl(endpoint: string, id?: string): string {
	return id ? `${BASE_API_URL}/${endpoint}/${id}/` : `${BASE_API_URL}/${endpoint}/`;
}

function draftActionUrl(frameworkId: string, action: string): string {
	return `${BASE_API_URL}/frameworks/${frameworkId}/${action}/`;
}

export const POST: RequestHandler = async ({ fetch, request, url, params }) => {
	const urlAction = url.searchParams.get('_action');

	if (urlAction === 'upload-image') {
		const formData = await request.formData();
		const file = formData.get('file');
		if (!file || !(file instanceof File)) {
			return new Response(JSON.stringify({ error: 'No file provided' }), { status: 400 });
		}
		const proxyForm = new FormData();
		proxyForm.append('file', new Blob([await file.arrayBuffer()], { type: file.type }), file.name);
		const apiUrl = `${BASE_API_URL}/frameworks/${params.id}/upload-image/`;
		const res = await fetch(apiUrl, { method: 'POST', body: proxyForm });
		const data = await res.json();
		return new Response(JSON.stringify(data), {
			status: res.status,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const body = await request.json();

	// Draft workflow actions (sent via _action in body)
	if (body._action === 'start-editing') {
		return proxyFetch(fetch, draftActionUrl(params.id, 'start-editing'), 'POST');
	}
	if (body._action === 'publish-draft-preview') {
		return proxyFetch(fetch, draftActionUrl(params.id, 'publish-draft-preview'), 'POST');
	}
	if (body._action === 'publish-draft') {
		return proxyFetch(fetch, draftActionUrl(params.id, 'publish-draft'), 'POST');
	}
	if (body._action === 'discard-draft') {
		return proxyFetch(fetch, draftActionUrl(params.id, 'discard-draft'), 'POST');
	}

	// Legacy: generic entity creation
	const { endpoint, payload } = body;
	return proxyFetch(fetch, entityUrl(endpoint), 'POST', payload);
};

export const PATCH: RequestHandler = async ({ fetch, request, params }) => {
	const body = await request.json();

	// Draft workflow: save-draft
	if (body._action === 'save-draft') {
		return proxyFetch(fetch, draftActionUrl(params.id, 'save-draft'), 'PATCH', {
			editing_draft: body.editing_draft
		});
	}

	// Legacy: generic entity update
	const { endpoint, id, payload } = body;
	return proxyFetch(fetch, entityUrl(endpoint, id), 'PATCH', payload);
};

export const GET: RequestHandler = async ({ fetch, url, params }) => {
	const action = url.searchParams.get('_action');

	if (action === 'serve-image') {
		const attachmentId = url.searchParams.get('attachment_id');
		if (!attachmentId) {
			return new Response(JSON.stringify({ error: 'attachment_id required' }), {
				status: 400
			});
		}
		const apiUrl = `${BASE_API_URL}/frameworks/${params.id}/serve-image/${attachmentId}/`;
		const res = await fetch(apiUrl);
		if (!res.ok) {
			return new Response(null, { status: res.status });
		}
		const contentType = res.headers.get('Content-Type') || 'application/octet-stream';
		const body = await res.arrayBuffer();
		return new Response(body, {
			status: 200,
			headers: { 'Content-Type': contentType }
		});
	}

	if (action === 'export-yaml') {
		const apiUrl = `${BASE_API_URL}/frameworks/${params.id}/export-yaml/`;
		const res = await fetch(apiUrl);
		if (!res.ok) {
			return new Response(null, { status: res.status });
		}
		const body = await res.arrayBuffer();
		return new Response(body, {
			status: 200,
			headers: {
				'Content-Type': res.headers.get('Content-Type') || 'application/x-yaml',
				'Content-Disposition': res.headers.get('Content-Disposition') || ''
			}
		});
	}

	return new Response(null, { status: 404 });
};

export const DELETE: RequestHandler = async ({ fetch, request }) => {
	const { endpoint, id } = await request.json();
	return proxyFetch(fetch, entityUrl(endpoint, id), 'DELETE');
};
