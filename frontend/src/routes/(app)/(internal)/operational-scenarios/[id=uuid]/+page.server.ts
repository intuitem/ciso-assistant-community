import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { getModelInfo } from '$lib/utils/crud';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { loadDetail } from '$lib/utils/load';

export const load: PageServerLoad = async (event) => {
	const URLModel = 'operational-scenarios';
	const model = getModelInfo(URLModel);
	const detail = await loadDetail({ event, model: model, id: event.params.id });

	const headData: Record<string, string> = listViewFields[URLModel as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[URLModel as urlModel].head[index];
			return obj;
		},
		{}
	);

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	const likelihoodChoicesEndpoint = `${BASE_API_URL}/ebios-rm/studies/${detail.data.ebios_rm_study.id}/likelihood/`;
	const likelihoodChoicesResponse = await event.fetch(likelihoodChoicesEndpoint);

	if (likelihoodChoicesResponse.ok) {
		detail.relatedModels['operating-modes'].selectOptions['likelihood'] =
			await likelihoodChoicesResponse.json().then((data) =>
				Object.entries(data).map(([key, value]) => ({
					label: value,
					value: parseInt(key)
				}))
			);
	} else {
		console.error(`Failed to fetch data for likelihood: ${likelihoodChoicesResponse.statusText}`);
	}

	return { ...detail, table };
};

export const actions: Actions = {
	create: async (event) => {
		return defaultWriteFormAction({
			event,
			urlModel: 'operating-modes',
			action: 'create'
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: 'operating-modes' });
	}
};
