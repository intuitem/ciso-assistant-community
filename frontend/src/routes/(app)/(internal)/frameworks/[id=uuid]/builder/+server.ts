import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

async function proxyRequest(
	fetch: typeof globalThis.fetch,
	method: string,
	endpoint: string,
	id?: string,
	payload?: unknown
) {
	const url = id ? `${BASE_API_URL}/${endpoint}/${id}/` : `${BASE_API_URL}/${endpoint}/`;

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

export const POST: RequestHandler = async ({ fetch, request, url }) => {
	const action = url.searchParams.get('_action');

	if (action === 'upload-image') {
		const nodeId = url.searchParams.get('node_id');
		if (!nodeId) {
			return new Response(JSON.stringify({ error: 'node_id required' }), { status: 400 });
		}
		const formData = await request.formData();
		const file = formData.get('file');
		if (!file || !(file instanceof File)) {
			return new Response(JSON.stringify({ error: 'No file provided' }), { status: 400 });
		}
		const proxyForm = new FormData();
		proxyForm.append('file', new Blob([await file.arrayBuffer()], { type: file.type }), file.name);
		const apiUrl = `${BASE_API_URL}/requirement-nodes/${nodeId}/upload-image/`;
		const res = await fetch(apiUrl, { method: 'POST', body: proxyForm });
		const data = await res.json();
		return new Response(JSON.stringify(data), {
			status: res.status,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const { endpoint, payload } = await request.json();
	return proxyRequest(fetch, 'POST', endpoint, undefined, payload);
};

export const PATCH: RequestHandler = async ({ fetch, request }) => {
	const { endpoint, id, payload } = await request.json();
	return proxyRequest(fetch, 'PATCH', endpoint, id, payload);
};

export const GET: RequestHandler = async ({ fetch, url }) => {
	const action = url.searchParams.get('_action');

	if (action === 'serve-image') {
		const nodeId = url.searchParams.get('node_id');
		const attachmentId = url.searchParams.get('attachment_id');
		if (!nodeId || !attachmentId) {
			return new Response(JSON.stringify({ error: 'node_id and attachment_id required' }), {
				status: 400
			});
		}
		const apiUrl = `${BASE_API_URL}/requirement-nodes/${nodeId}/serve-image/${attachmentId}/`;
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

	return new Response(null, { status: 404 });
};

export const DELETE: RequestHandler = async ({ fetch, request }) => {
	const { endpoint, id } = await request.json();
	return proxyRequest(fetch, 'DELETE', endpoint, id);
};
