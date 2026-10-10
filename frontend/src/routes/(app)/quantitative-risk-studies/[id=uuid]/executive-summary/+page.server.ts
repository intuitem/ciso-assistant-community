import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const { id } = event.params;

	// Load executive summary data asynchronously
	const getExecutiveSummary = async () => {
		try {
			const url = `${BASE_API_URL}/crq/quantitative-risk-studies/${id}/executive-summary/`;
			const response = await event.fetch(url);
			if (!response.ok) {
				throw new Error(
					`Failed to fetch executive summary: ${response.status} ${response.statusText}`
				);
			}
			return await response.json();
		} catch (error) {
			console.error('Failed to fetch executive summary data:', error);
			return null;
		}
	};

	// Load combined LEC data asynchronously
	const getCombinedLec = async () => {
		try {
			const url = `${BASE_API_URL}/crq/quantitative-risk-studies/${id}/combined-lec/`;
			const response = await event.fetch(url);
			if (!response.ok) {
				throw new Error(`Failed to fetch combined LEC: ${response.status} ${response.statusText}`);
			}
			return await response.json();
		} catch (error) {
			console.error('Failed to fetch combined LEC data:', error);
			return null;
		}
	};

	// Load ALE comparison data asynchronously
	const getAleComparison = async () => {
		try {
			const url = `${BASE_API_URL}/crq/quantitative-risk-studies/${id}/ale-comparison/`;
			const response = await event.fetch(url);
			if (!response.ok) {
				throw new Error(
					`Failed to fetch ALE comparison: ${response.status} ${response.statusText}`
				);
			}
			return await response.json();
		} catch (error) {
			console.error('Failed to fetch ALE comparison data:', error);
			return null;
		}
	};

	return {
		title: 'Executive summary',
		stream: {
			executiveSummary: getExecutiveSummary(),
			combinedLec: getCombinedLec(),
			aleComparison: getAleComparison()
		}
	};
};
