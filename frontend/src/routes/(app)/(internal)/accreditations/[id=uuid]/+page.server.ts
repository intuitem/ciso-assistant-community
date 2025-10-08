import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('accreditations');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	return data;
};
