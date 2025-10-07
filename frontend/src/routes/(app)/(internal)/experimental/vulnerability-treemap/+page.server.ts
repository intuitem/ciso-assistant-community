import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import * as m from '$paraglide/messages';

export const load: PageServerLoad = async ({ fetch }) => {
	const getTreemapData = async () => {
		try {
			const response = await fetch(`${BASE_API_URL}/vulnerabilities/treemap_data/`);
			const data = await response.json();
			return data;
		} catch (error) {
			console.error('Failed to fetch vulnerability treemap data:', error);
			return [];
		}
	};

	return {
		title: m.vulnerabilityTreemap(),
		stream: {
			treemapData: getTreemapData()
		}
	};
};
