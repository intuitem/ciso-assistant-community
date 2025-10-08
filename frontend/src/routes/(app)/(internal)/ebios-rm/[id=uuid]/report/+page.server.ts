import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch, parent }) => {
	const endpoint = `${BASE_API_URL}/ebios-rm/studies/${params.id}/report-data/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	const interface_settings = await fetch(`${BASE_API_URL}/settings/general/object`).then((res) =>
		res.json()
	);

	// Get featureflags from parent layout
	const { featureflags } = await parent();

	return {
		reportData: data,
		useBubbles: interface_settings.interface_agg_scenario_matrix,
		inherentRiskEnabled: featureflags?.inherent_risk || false
	};
};
