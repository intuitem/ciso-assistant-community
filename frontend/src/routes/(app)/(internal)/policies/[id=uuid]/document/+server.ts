import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Create a policy document
export const POST: RequestHandler = async ({ fetch, request }) => {
	const body = await request.json();
	const action = body._action;
	delete body._action;

	let endpoint: string;
	let method = 'POST';

	switch (action) {
		case 'create-document':
			endpoint = `${BASE_API_URL}/policy-documents/`;
			break;
		case 'create-new-draft':
			endpoint = `${BASE_API_URL}/policy-documents/${body.document_id}/create-new-draft/`;
			delete body.document_id;
			break;
		case 'save-revision':
			endpoint = `${BASE_API_URL}/policy-document-revisions/${body.revision_id}/`;
			delete body.revision_id;
			method = 'PATCH';
			break;
		case 'submit-for-review':
			endpoint = `${BASE_API_URL}/policy-document-revisions/${body.revision_id}/submit-for-review/`;
			delete body.revision_id;
			break;
		case 'approve':
			endpoint = `${BASE_API_URL}/policy-document-revisions/${body.revision_id}/approve/`;
			delete body.revision_id;
			break;
		case 'request-changes':
			endpoint = `${BASE_API_URL}/policy-document-revisions/${body.revision_id}/request-changes/`;
			delete body.revision_id;
			break;
		default:
			error(400, { message: 'Unknown action' });
	}

	const res = await fetch(endpoint, {
		method,
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	return json(await res.json(), { status: res.status });
};

// Proxy GET requests for revisions, diffs, PDF export
export const GET: RequestHandler = async ({ fetch, url }) => {
	const action = url.searchParams.get('_action');

	let endpoint: string;

	switch (action) {
		case 'revisions': {
			const documentId = url.searchParams.get('document');
			endpoint = `${BASE_API_URL}/policy-document-revisions/?document=${documentId}&ordering=-version_number`;
			break;
		}
		case 'revision': {
			const revisionId = url.searchParams.get('revision_id');
			endpoint = `${BASE_API_URL}/policy-document-revisions/${revisionId}/`;
			break;
		}
		case 'diff': {
			const revisionId = url.searchParams.get('revision_id');
			const otherId = url.searchParams.get('other_id');
			endpoint = `${BASE_API_URL}/policy-document-revisions/${revisionId}/diff/${otherId}/`;
			break;
		}
		case 'export-pdf': {
			const revisionId = url.searchParams.get('revision_id');
			endpoint = `${BASE_API_URL}/policy-document-revisions/${revisionId}/export-pdf/`;
			const res = await fetch(endpoint);
			if (!res.ok) {
				error(res.status as NumericRange<400, 599>, 'PDF export failed');
			}
			const pdfBuffer = await res.arrayBuffer();
			return new Response(pdfBuffer, {
				status: 200,
				headers: {
					'Content-Type': 'application/pdf',
					'Content-Disposition': res.headers.get('Content-Disposition') || 'attachment'
				}
			});
		}
		default:
			error(400, { message: 'Unknown action' });
	}

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	return json(await res.json());
};

// Delete a document or revision
export const DELETE: RequestHandler = async ({ fetch, url }) => {
	const type = url.searchParams.get('_type');
	const id = url.searchParams.get('id');

	if (!type || !id) {
		error(400, { message: 'Missing _type or id parameter' });
	}

	let endpoint: string;
	switch (type) {
		case 'document':
			endpoint = `${BASE_API_URL}/policy-documents/${id}/`;
			break;
		case 'revision':
			endpoint = `${BASE_API_URL}/policy-document-revisions/${id}/`;
			break;
		default:
			error(400, { message: 'Unknown type' });
	}

	const res = await fetch(endpoint, { method: 'DELETE' });
	if (!res.ok) {
		const body = await res.text();
		error(res.status as NumericRange<400, 599>, body || 'Delete failed');
	}

	return new Response(null, { status: 204 });
};
