import { BASE_API_URL } from '#lib/utils/constants.js';
import { isMaskedPlaceholder } from '#lib/utils/related-visibility.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch, parent }) => {
	const endpoint = `${BASE_API_URL}/ebios-rm/studies/${params.id}/report-data/`;

	const res = await fetch(endpoint);

	// The report lists what the user can see: the linked objects the backend
	// masked are taken out of every list, and counted for the note at the top.
	let hiddenObjects = 0;
	const withoutMasked = (value: unknown): unknown => {
		if (Array.isArray(value)) {
			const visible = value.filter((item) => !isMaskedPlaceholder(item));
			hiddenObjects += value.length - visible.length;
			return visible.map(withoutMasked);
		}
		if (value && typeof value === 'object') {
			return Object.fromEntries(
				Object.entries(value).map(([key, item]) => [key, withoutMasked(item)])
			);
		}
		return value;
	};
	const data = withoutMasked(await res.json()) as Record<string, any>;

	const interface_settings = await fetch(`${BASE_API_URL}/settings/general/object/`).then((res) =>
		res.json()
	);

	// Get featureflags from parent layout
	const { featureflags } = await parent();

	return {
		reportData: data,
		hiddenObjects,
		useBubbles: interface_settings.interface_agg_scenario_matrix,
		inherentRiskEnabled: featureflags?.inherent_risk || false
	};
};
