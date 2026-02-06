import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

import type { PageServerLoad } from './$types';
import { loadDetail } from '$lib/utils/load';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';

export const load: PageServerLoad = async (event) => {
	const EbiosRMSchema = modelSchema('ebios-rm');
	const loadData = await loadDetail({
		event,
		model: getModelInfo('ebios-rm'),
		id: event.params.id
	});

	const ebiosRMStudy = loadData.data;

	const initialDataDuplicate = {
		name: ebiosRMStudy.name,
		description: ebiosRMStudy.description,
		version: ebiosRMStudy.version
	};

	const ebiosRMDuplicateForm = await superValidate(initialDataDuplicate, zod(EbiosRMSchema), {
		errors: false
	});

	loadData.ebiosRMDuplicateForm = ebiosRMDuplicateForm;
	return loadData;
};
