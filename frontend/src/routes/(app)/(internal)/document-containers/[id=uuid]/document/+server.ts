import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

function assertFeatureEnabled(locals: App.Locals) {
	if (!locals.featureflags?.document_management) {
		error(403, { message: 'Document management feature is disabled' });
	}
}

// Create a document or upload image
export const POST: RequestHandler = async ({ fetch, request, url, locals, params }) => {
	assertFeatureEnabled(locals);

	// Add a new locale variant with an uploaded file, atomically (multipart).
	if (url.searchParams.get('_action') === 'add-locale') {
		const incoming = await request.formData();
		const file = incoming.get('file') as File | null;
		const outgoing = new FormData();
		if (file) {
			const bytes = new Uint8Array(await file.arrayBuffer());
			outgoing.append('file', new Blob([bytes], { type: file.type }), file.name);
		}
		outgoing.append('locale', String(incoming.get('locale') ?? ''));
		outgoing.append('source', String(incoming.get('source') ?? 'uploaded'));
		const res = await fetch(`${BASE_API_URL}/document-containers/${params.id}/add-locale/`, {
			method: 'POST',
			body: outgoing
		});
		if (!res.ok) {
			error(res.status as NumericRange<400, 599>, await res.text());
		}
		return json(await res.json(), { status: res.status });
	}

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

	// Upload a file as a new draft revision (uploaded documents).
	if (url.searchParams.get('_action') === 'upload-revision') {
		const documentId = url.searchParams.get('document_id');
		if (!documentId) {
			error(400, { message: 'Missing document_id' });
		}
		const incoming = await request.formData();
		const file = incoming.get('file') as File | null;
		if (!file) {
			error(400, { message: 'Missing file' });
		}
		const bytes = new Uint8Array(await file.arrayBuffer());
		const outgoing = new FormData();
		outgoing.append('file', new Blob([bytes], { type: file.type }), file.name);
		const res = await fetch(`${BASE_API_URL}/managed-documents/${documentId}/upload-revision/`, {
			method: 'POST',
			body: outgoing
		});
		if (!res.ok) {
			error(res.status as NumericRange<400, 599>, await res.text());
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
		case 'add-locale':
			endpoint = `${BASE_API_URL}/document-containers/${params.id}/add-locale/`;
			break;
		case 'create-new-draft':
			endpoint = `${BASE_API_URL}/managed-documents/${body.document_id}/create-new-draft/`;
			delete body.document_id;
			break;
		case 'link-revision':
			endpoint = `${BASE_API_URL}/managed-documents/${body.document_id}/link-revision/`;
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
		case 'publish':
			endpoint = `${BASE_API_URL}/document-revisions/${body.revision_id}/publish/`;
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

	const req = (key: string): string => {
		const value = url.searchParams.get(key);
		if (!value) error(400, { message: `Missing ${key}` });
		return value;
	};

	let endpoint: string;

	switch (action) {
		case 'references': {
			const refRes = await fetch(`${BASE_API_URL}/document-containers/${params.id}/references/`);
			if (!refRes.ok) {
				error(refRes.status as NumericRange<400, 599>, await refRes.json());
			}
			return json(await refRes.json());
		}
		case 'templates': {
			const lang = url.searchParams.get('lang') || '';
			const docType = url.searchParams.get('document_type') || '';
			const qp = new URLSearchParams();
			if (lang) qp.set('lang', lang);
			if (docType) qp.set('document_type', docType);
			const templatesEndpoint = `${BASE_API_URL}/managed-documents/templates/${qp.toString() ? `?${qp}` : ''}`;
			const templatesRes = await fetch(templatesEndpoint);
			if (!templatesRes.ok) {
				error(templatesRes.status as NumericRange<400, 599>, await templatesRes.json());
			}
			return json(await templatesRes.json());
		}
		case 'documents-by-locale': {
			const locale = req('locale');
			const qp = new URLSearchParams({ container: params.id, locale });
			const docsRes = await fetch(`${BASE_API_URL}/managed-documents/?${qp}`);
			if (!docsRes.ok) {
				error(docsRes.status as NumericRange<400, 599>, await docsRes.json());
			}
			const docsData = await docsRes.json();
			const doc = docsData.results?.[0] || null;
			return json(doc);
		}
		case 'revisions': {
			const documentId = req('document');
			endpoint = `${BASE_API_URL}/document-revisions/?document=${documentId}&ordering=-version_number`;
			break;
		}
		case 'revision': {
			endpoint = `${BASE_API_URL}/document-revisions/${req('revision_id')}/`;
			break;
		}
		case 'diff': {
			endpoint = `${BASE_API_URL}/document-revisions/${req('revision_id')}/diff/${req('other_id')}/`;
			break;
		}
		case 'editing-status': {
			endpoint = `${BASE_API_URL}/document-revisions/${req('revision_id')}/editing-status/`;
			break;
		}
		case 'edit-history': {
			endpoint = `${BASE_API_URL}/document-revisions/${req('revision_id')}/edit-history/`;
			break;
		}
		case 'edit-snapshot': {
			endpoint = `${BASE_API_URL}/document-revisions/${req('revision_id')}/edit-snapshot/${req('edit_id')}/`;
			break;
		}
		case 'export-pdf': {
			endpoint = `${BASE_API_URL}/document-revisions/${req('revision_id')}/export-pdf/`;
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
			const attachmentId = req('attachment_id');
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
					'Cache-Control': 'private, max-age=3600'
				}
			});
		}
		case 'edit-diff': {
			endpoint = `${BASE_API_URL}/document-revisions/${req('revision_id')}/edit-diff/${req('edit_a_id')}/${req('edit_b_id')}/`;
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
