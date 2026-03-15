import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const { parent_url_slug, parent_id, m2m_field, item_ids } = await request.json();

	if (!parent_url_slug || !parent_id || !m2m_field || !item_ids?.length) {
		return new Response(
			JSON.stringify({ detail: 'Missing parent_url_slug, parent_id, m2m_field, or item_ids' }),
			{
				status: 400,
				headers: { 'Content-Type': 'application/json' }
			}
		);
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
