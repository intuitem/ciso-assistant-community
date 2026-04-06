import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { LayoutServerLoad } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { modelSchema } from '$lib/utils/schemas';

export const load: LayoutServerLoad = async (event) => {
	const modelInfo = getModelInfo('applied-controls');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	// Duplicate form for applied controls
	const appliedControlSchema = modelSchema('applied-controls');
	const appliedControl = data.data;
	const initialDataDuplicate = {
		name: appliedControl.name,
		description: appliedControl.description,
		folder: appliedControl.folder.id
	};

	const appliedControlDuplicateForm = await superValidate(
		initialDataDuplicate,
		zod(appliedControlSchema),
		{
			errors: false
		}
	);

	data.duplicateForm = appliedControlDuplicateForm;

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
