import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { LayoutServerLoad } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const load: LayoutServerLoad = async (event) => {
	const modelInfo = getModelInfo('applied-controls');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	let dryRunData: [string, string][] = [];
	if (data.data.reference_control) {
		const endpoint = `${BASE_API_URL}/applied-controls/${event.params.id}/sync-to-reference-control/?dry_run=true`;
		const response = await event.fetch(endpoint, {
			method: 'POST'
		});

		if (response.ok) {
			dryRunData = await response.json();
		} else {
			console.error('Failed to get dry run data.');
		}
	}

	data.dryRunData = dryRunData;
	return data;
};
