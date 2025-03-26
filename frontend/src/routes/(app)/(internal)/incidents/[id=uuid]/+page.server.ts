import { getModelInfo } from '$lib/utils/crud';

import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';

import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('incidents');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	return data;
};

export const actions: Actions = {
	create: async (event) => {
		const redirectToWrittenObject = Boolean(event.params.model === 'perimeters');
		return defaultWriteFormAction({
			event,
			urlModel: 'timeline-entries',
			action: 'create',
			redirectToWrittenObject
		});
	},
	delete: async (event) => {
		console.log('delete');
		return nestedDeleteFormAction({ event });
	}
};
