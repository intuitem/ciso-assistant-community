import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	return loadDetail({ event, model: getModelInfo('entity-assessments'), id: event.params.id });
};
