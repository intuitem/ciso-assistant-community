import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('strategic-scenarios'),
		id: event.params.id
	});

	// Fetch attack paths for this strategic scenario
	const attackPathsResponse = await event.fetch(
		`${BASE_API_URL}/ebios-rm/attack-paths/?strategic_scenario=${event.params.id}`
	);
	const attackPathsData = attackPathsResponse.ok
		? await attackPathsResponse.json()
		: { results: [] };

	// Fetch feared events for this strategic scenario
	// If a focused_feared_event is set, only show that one feared event
	const focusedFearedEvent = detailData.data.focused_feared_event;
	const fearedEventsIds = focusedFearedEvent
		? [focusedFearedEvent.id]
		: detailData.data.feared_events?.map((fe: any) => fe.id) || [];
	const fearedEventsData = [];

	if (fearedEventsIds.length > 0) {
		for (const feId of fearedEventsIds) {
			const feResponse = await event.fetch(`${BASE_API_URL}/ebios-rm/feared-events/${feId}/`);
			if (feResponse.ok) {
				fearedEventsData.push(await feResponse.json());
			}
		}
	}

	return {
		...detailData,
		attackPaths: attackPathsData.results || [],
		fearedEventsWithAssets: fearedEventsData,
		isFocusedOnFearedEvent: !!focusedFearedEvent
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
