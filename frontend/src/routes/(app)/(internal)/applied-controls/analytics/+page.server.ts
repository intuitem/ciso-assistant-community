import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	// Forward the user-applied filters from the table page so analytics reflect them.
	const queryParams = new URLSearchParams();
	for (const [key, value] of url.searchParams.entries()) {
		if (!['backUrl', 'backLabel'].includes(key)) {
			queryParams.append(key, value);
		}
	}
	const qs = queryParams.toString();
	const endpoint = `${BASE_API_URL}/applied-controls/analytics/${qs ? `?${qs}` : ''}`;

	const res = await fetch(endpoint);
	const analytics = res.ok ? await res.json() : null;

	const rawBackUrl = url.searchParams.get('backUrl') ?? '/applied-controls';
	const backUrl =
		rawBackUrl.startsWith('/') && !rawBackUrl.startsWith('//') ? rawBackUrl : '/applied-controls';
	const backLabel = url.searchParams.get('backLabel') ?? 'Applied Controls';

	return {
		analytics,
		hasFilters: qs.length > 0,
		filterSearch: qs ? `?${qs}` : '',
		backUrl,
		backLabel
	};
};
