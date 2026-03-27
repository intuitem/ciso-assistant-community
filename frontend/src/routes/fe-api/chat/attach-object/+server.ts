import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SLUG_RE = /^[a-z0-9-/]+$/;

export const POST: RequestHandler = async ({ fetch, request }) => {
	let body: Record<string, unknown>;
	try {
		body = await request.json();
	} catch {
		return new Response(JSON.stringify({ detail: 'Invalid JSON' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const { parent_url_slug, parent_id, m2m_field, item_ids } = body as Record<string, any>;

	if (!parent_url_slug || !parent_id || !m2m_field || !item_ids?.length) {
		return new Response(
			JSON.stringify({ detail: 'Missing parent_url_slug, parent_id, m2m_field, or item_ids' }),
			{
				status: 400,
				headers: { 'Content-Type': 'application/json' }
			}
		);
	}

	// Validate to prevent path traversal
	if (!SLUG_RE.test(parent_url_slug) || !UUID_RE.test(parent_id)) {
		return new Response(JSON.stringify({ detail: 'Invalid slug or ID format' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	// First, get the current object to read existing M2M values
	const getRes = await fetch(`${BASE_API_URL}/${parent_url_slug}/${parent_id}/`, {
		method: 'GET',
		headers: { 'Content-Type': 'application/json' }
	});

	if (!getRes.ok) {
		return new Response(JSON.stringify({ detail: 'Failed to fetch parent object' }), {
			status: getRes.status,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const parentData = await getRes.json();

	// Merge existing IDs with new ones (avoid duplicates)
	const existingIds: string[] = Array.isArray(parentData[m2m_field]) ? parentData[m2m_field] : [];
	const mergedIds = [...new Set([...existingIds, ...item_ids])];

	// PATCH to update only the M2M field
	const patchRes = await fetch(`${BASE_API_URL}/${parent_url_slug}/${parent_id}/`, {
		method: 'PATCH',
		body: JSON.stringify({ [m2m_field]: mergedIds }),
		headers: { 'Content-Type': 'application/json' }
	});

	const responseData = await patchRes.text();

	return new Response(responseData, {
		status: patchRes.status,
		headers: {
			'Content-Type': patchRes.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
