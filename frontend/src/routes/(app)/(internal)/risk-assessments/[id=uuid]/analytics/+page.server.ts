import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, parent }) => {
	const parentData = await parent();
	const endpoint = `${BASE_API_URL}/risk-assessments/${params.id}/risk_analytics/`;

	const analyticsPromise = fetch(endpoint)
		.then((res) => {
			if (!res.ok) {
				console.error(`risk_analytics failed: ${res.status} ${res.statusText}`);
				throw new Error(`API error: ${res.status}`);
			}
			return res.json();
		})
		.catch((err) => {
			console.error('risk_analytics fetch error:', err);
			return {
				threats: { labels: [], values: [] },
				treatment: { labels: [], values: [] },
				strength_of_knowledge: { labels: [], values: [] },
				assets: { labels: [], values: [] },
				risk_reduction: []
			};
		});

	return {
		risk_assessment: parentData.risk_assessment,
		title: 'Analytics',
		stream: {
			analytics: analyticsPromise
		}
	};
};
