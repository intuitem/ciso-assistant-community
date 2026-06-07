import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, url }) => {
	const targetId = url.searchParams.get('target');
	const sourceId = url.searchParams.get('source');

	if (!targetId || !sourceId) {
		throw error(400, 'Both target and source audit IDs are required');
	}

	const previewEndpoint = `${BASE_API_URL}/compliance-assessments/${targetId}/map_from_preview/?source_audit_id=${sourceId}`;

	const previewData = await fetch(previewEndpoint).then((res) => {
		if (!res.ok) {
			if (res.status === 404) throw error(404, 'One or both audits not found');
			if (res.status === 403) throw error(403, 'Permission denied');
			if (res.status === 400) throw error(400, 'No mapping path found between these frameworks');
			throw error(500, 'Failed to load mapping preview');
		}
		return res.json();
	});

	return {
		previewData,
		targetId,
		sourceId,
		title: `Mapping preview: ${previewData.target_audit.name}`
	};
}) satisfies PageServerLoad;
