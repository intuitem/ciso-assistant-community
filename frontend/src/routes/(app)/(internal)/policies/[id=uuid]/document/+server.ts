import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

function assertFeatureEnabled(locals: App.Locals) {
	if (!locals.featureflags?.policy_documents) {
		error(403, { message: 'Policy documents feature is disabled' });
	}
}

// Create a policy document or upload image
export const POST: RequestHandler = async ({ fetch, request, url, locals }) => {
	assertFeatureEnabled(locals);

	// Handle image uploads — read file into memory and forward as multipart
	if (url.searchParams.get('_action') === 'upload-image') {
		const documentId = url.searchParams.get('document_id');
		if (!documentId) {
			error(400, { message: 'Missing document_id' });
		}
		const incoming = await request.formData();
		const file = incoming.get('file') as File | null;
		if (!file) {
			error(400, { message: 'Missing file' });
		}
		// Rebuild FormData with a concrete Blob so fetch serialises it correctly
		const bytes = new Uint8Array(await file.arrayBuffer());
		const outgoing = new FormData();
		outgoing.append('file', new Blob([bytes], { type: file.type }), file.name);
		const endpoint = `${BASE_API_URL}/managed-documents/${documentId}/upload-image/`;
		const res = await fetch(endpoint, {
			method: 'POST',
			body: outgoing
		});
		if (!res.ok) {
			const errorBody = await res.text();
			error(res.status as NumericRange<400, 599>, errorBody);
		}
		return json(await res.json(), { status: res.status });
	}

	const body = await request.json();
	const action = body._action;
	delete body._action;

	let endpoint: string;
	let method = 'POST';

	switch (action) {
		case 'create-document':
			endpoint = `${BASE_API_URL}/managed-documents/`;
			break;
		case 'create-new-draft':
			endpoint = `${BASE_API_URL}/managed-documents/${body.document_id}/create-new-draft/`;
			delete body.document_id;
			break;
		case 'save-revision':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/`;
			delete body.revision_id;
			method = 'PATCH';
			break;
		case 'submit-for-review':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/submit-for-review/`;
			delete body.revision_id;
			break;
		case 'approve':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/approve/`;
			delete body.revision_id;
			break;
		case 'request-changes':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/request-changes/`;
			delete body.revision_id;
			break;
		case 'start-editing':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/start-editing/`;
			delete body.revision_id;
			break;
		case 'stop-editing':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/stop-editing/`;
			delete body.revision_id;
			break;
		case 'take-over-editing':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/take-over-editing/`;
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
export const GET: RequestHandler = async ({ fetch, url, params, locals }) => {
	assertFeatureEnabled(locals);

	const action = url.searchParams.get('_action');

	let endpoint: string;

	switch (action) {
		case 'documents-by-locale': {
			const locale = url.searchParams.get('locale');
			const docsEndpoint = `${BASE_API_URL}/managed-documents/?policy=${params.id}&locale=${locale}`;
			const docsRes = await fetch(docsEndpoint);
			if (!docsRes.ok) {
				error(docsRes.status as NumericRange<400, 599>, await docsRes.json());
			}
			const docsData = await docsRes.json();
			const doc = docsData.results?.[0] || null;
			return json(doc);
		}
		case 'revisions': {
			const documentId = url.searchParams.get('document');
			endpoint = `${BASE_API_URL}/document-revisions/?document=${documentId}&ordering=-version_number`;
			break;
		}
		case 'revision': {
			const revisionId = url.searchParams.get('revision_id');
			endpoint = `${BASE_API_URL}/document-revisions/${revisionId}/`;
			break;
		}
		case 'diff': {
			const revisionId = url.searchParams.get('revision_id');
			const otherId = url.searchParams.get('other_id');
			endpoint = `${BASE_API_URL}/document-revisions/${revisionId}/diff/${otherId}/`;
			break;
		}
		case 'editing-status': {
			const revisionId = url.searchParams.get('revision_id');
			endpoint = `${BASE_API_URL}/document-revisions/${revisionId}/editing-status/`;
			break;
		}
		case 'edit-history': {
			const revisionId = url.searchParams.get('revision_id');
			endpoint = `${BASE_API_URL}/document-revisions/${revisionId}/edit-history/`;
			break;
		}
		case 'edit-snapshot': {
			const revisionId = url.searchParams.get('revision_id');
			const editId = url.searchParams.get('edit_id');
			endpoint = `${BASE_API_URL}/document-revisions/${revisionId}/edit-snapshot/${editId}/`;
			break;
		}
		case 'export-pdf': {
			const revisionId = url.searchParams.get('revision_id');
			endpoint = `${BASE_API_URL}/document-revisions/${revisionId}/export-pdf/`;
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
		case 'serve-image': {
			const attachmentId = url.searchParams.get('attachment_id');
			const imageEndpoint = `${BASE_API_URL}/document-attachments/${attachmentId}/file/`;
			const res = await fetch(imageEndpoint);
			if (!res.ok) {
				error(res.status as NumericRange<400, 599>, 'Image fetch failed');
			}
			const imageBuffer = await res.arrayBuffer();
			return new Response(imageBuffer, {
				status: 200,
				headers: {
					'Content-Type': res.headers.get('Content-Type') || 'application/octet-stream',
					'Cache-Control': 'public, max-age=3600'
				}
			});
		}
		case 'edit-diff': {
			const revisionId = url.searchParams.get('revision_id');
			const editAId = url.searchParams.get('edit_a_id');
			const editBId = url.searchParams.get('edit_b_id');
			endpoint = `${BASE_API_URL}/document-revisions/${revisionId}/edit-diff/${editAId}/${editBId}/`;
			break;
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
export const DELETE: RequestHandler = async ({ fetch, url, locals }) => {
	assertFeatureEnabled(locals);

	const type = url.searchParams.get('_type');
	const id = url.searchParams.get('id');

	if (!type || !id) {
		error(400, { message: 'Missing _type or id parameter' });
	}

	let endpoint: string;
	switch (type) {
		case 'document':
			endpoint = `${BASE_API_URL}/managed-documents/${id}/`;
			break;
		case 'revision':
			endpoint = `${BASE_API_URL}/document-revisions/${id}/`;
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
