import { getModelInfo } from '#lib/utils/crud.js';
import { loadDetail } from '#lib/utils/load.js';
import { fetchOccurrenceHistory } from '#lib/utils/taskOccurrences.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('task-templates');

	const data = await loadDetail({ event, model: modelInfo, id: event.params.id });

	const history = await fetchOccurrenceHistory(event.fetch, event.params.id);

	return { ...data, ...history };
};
