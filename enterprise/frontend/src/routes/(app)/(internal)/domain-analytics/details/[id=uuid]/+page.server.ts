import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { TODAY } from '$lib/utils/constants';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async ({ locals, fetch, params }) => {
	const req_applied_control_status = await fetch(`${BASE_API_URL}/applied-controls/per_status/`);
	const applied_control_status = await req_applied_control_status.json();

	const getMetrics = async () => {
		try {
			const response = await fetch(`${BASE_API_URL}/get_metrics/?folder=${params.id}`);
			const data = await response.json();
			return data.results;
		} catch (error) {
			console.error('Failed to fetch or parse metrics:', error);
			return null;
		}
	};
	const folderData = params.id
		? await fetch(`${BASE_API_URL}/folders/${params.id}/`)
				.then((res) => res.json())
				.then((res) => res.results || res)
				.catch((error) => {
					console.error('Failed to fetch folder data:', error);
					return null;
				})
		: null;
	const req_get_risks_count_per_level = await fetch(
		`${BASE_API_URL}/risk-scenarios/count_per_level/?folder=${params.id}`
	);
	const risks_count_per_level: {
		current: Record<string, any>[];
		residual: Record<string, any>[];
	} = await req_get_risks_count_per_level.json().then((res) => res.results);

	const threats_count = await fetch(
		`${BASE_API_URL}/threats/threats_count/?folder=${params.id}`
	).then((res) => res.json());

	const req_risk_assessments = await fetch(`${BASE_API_URL}/risk-assessments/`);
	const risk_assessments = await req_risk_assessments.json();

	return {
		risks_count_per_level,
		threats_count,
		folderData,
		risk_assessments: risk_assessments.results,
		applied_control_status: applied_control_status.results,
		user: locals.user,
		title: `${m.analytics()} - ${folderData?.name}`,
		stream: {
			metrics: getMetrics()
		}
	};
};
