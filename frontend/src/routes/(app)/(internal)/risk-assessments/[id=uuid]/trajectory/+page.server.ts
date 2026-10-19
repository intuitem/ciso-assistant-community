import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { ControlInfo } from '$lib/components/RiskMatrix/trajectory';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	try {
		const controls = await fetchAllPages<ControlInfo>(
			fetch,
			`${BASE_API_URL}/applied-controls/?risk_assessments=${params.id}`
		);
		return {
			controls: controls.map(({ id, name, ref_id, status, eta }) => ({
				id,
				name,
				ref_id,
				status,
				eta
			})),
			controlsError: false
		};
	} catch (error) {
		console.error('Failed to load applied controls for the risk trajectory', error);
		return { controls: [] as ControlInfo[], controlsError: true };
	}
};
