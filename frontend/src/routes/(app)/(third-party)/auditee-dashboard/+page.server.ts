import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/compliance-assessments/auditee-dashboard/`);
	const dashboard = await res.json();

	return {
		dashboard,
		title: m.auditDashboard()
	};
};
