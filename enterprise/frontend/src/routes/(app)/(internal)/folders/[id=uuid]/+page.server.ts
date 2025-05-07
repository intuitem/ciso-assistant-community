import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';

import type { Actions, PageServerLoad } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('folders'),
		id: event.params.id
	});

	// Fetch has_out_of_scope_objects
	const outOfScopeRes = await event.fetch(`${BASE_API_URL}/folders/${event.params.id}/check_out_of_scope_objects/`);
	if (!outOfScopeRes.ok) {
		throw new Error('Failed to check out-of-scope objects');
	}
	const { has_out_of_scope_objects, out_of_scope_objects } = await outOfScopeRes.json();
	return {
		...detailData,
		has_out_of_scope_objects,
		out_of_scope_objects
	};
};

export const actions: Actions = {
	create: async (event) => {
		const redirectToWrittenObject = false;
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
};
