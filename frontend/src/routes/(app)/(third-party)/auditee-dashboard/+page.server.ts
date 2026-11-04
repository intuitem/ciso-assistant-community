import { BASE_API_URL } from '#lib/utils/constants.js';
import type { PageServerLoad } from './$types';
import { m } from '#paraglide/messages.js';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/compliance-assessments/auditee-dashboard/`);
	const dashboard = await res.json();

	return {
		dashboard,
		title: m.auditDashboard()
	};
};
