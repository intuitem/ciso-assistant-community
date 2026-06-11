import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, parent }) => {
	const parentData = await parent();
	const baseEndpoint = `${BASE_API_URL}/risk-assessments/${params.id}`;

	const analyticsPromise = fetch(`${baseEndpoint}/risk_analytics/`)
		.then((res) => {
			if (!res.ok) throw new Error(`API error: ${res.status}`);
			return res.json();
		})
		.catch(() => ({
			threats: { labels: [], values: [] },
			treatment: { labels: [], values: [] },
			strength_of_knowledge: { labels: [], values: [] },
			assets: { labels: [], values: [] }
		}));

	const timelinePromise = fetch(`${baseEndpoint}/risk_timeline/`)
		.then((res) => {
			if (!res.ok) throw new Error(`API error: ${res.status}`);
			return res.json();
		})
		.catch(() => ({ timeline: [] }));

	return {
		risk_assessment: parentData.risk_assessment,
		title: 'Analytics',
		stream: {
			analytics: analyticsPromise,
			timeline: timelinePromise
		}
	};
};
