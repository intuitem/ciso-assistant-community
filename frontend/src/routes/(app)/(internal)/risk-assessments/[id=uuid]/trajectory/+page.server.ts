import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { ControlInfo } from '$lib/components/RiskMatrix/trajectory';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const controls = await fetchAllPages<ControlInfo>(
		fetch,
		`${BASE_API_URL}/applied-controls/?risk_assessments=${params.id}`
	).catch(() => []);

	return {
		controls: controls.map(({ id, name, ref_id, status, eta }) => ({
			id,
			name,
			ref_id,
			status,
			eta
		}))
	};
};
