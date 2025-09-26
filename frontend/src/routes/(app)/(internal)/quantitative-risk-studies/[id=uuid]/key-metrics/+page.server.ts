import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const { id } = event.params;

	// Load key metrics data asynchronously
	const getKeyMetrics = async () => {
		try {
			const url = `${BASE_API_URL}/crq/quantitative-risk-studies/${id}/key-metrics/`;
			const response = await event.fetch(url);
			if (!response.ok) {
				throw new Error(`Failed to fetch key metrics: ${response.status} ${response.statusText}`);
			}
			return await response.json();
		} catch (error) {
			console.error('Failed to fetch key metrics data:', error);
			return null;
		}
	};

	return {
		stream: {
			keyMetrics: getKeyMetrics()
		}
	};
};
