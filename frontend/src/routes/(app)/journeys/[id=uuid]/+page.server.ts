import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const dashboardResponse = await fetch(`${BASE_API_URL}/journeys/${params.id}/dashboard/`);

	if (!dashboardResponse.ok) {
		return {
			journey: null,
			steps: [],
			stats: {},
			title: 'journeyDashboard'
		};
	}

	const dashboard = await dashboardResponse.json();

	return {
		journey: dashboard.journey,
		steps: dashboard.steps,
		stats: dashboard.stats,
		title: 'journeyDashboard'
	};
};
