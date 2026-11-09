import { BASE_API_URL } from '#lib/utils/constants.js';
import type { PageServerLoad } from './$types';
import { m } from '#paraglide/messages.js';

export const load: PageServerLoad = async ({ fetch, parent }) => {
	const [res, { user }] = await Promise.all([
		fetch(`${BASE_API_URL}/compliance-assessments/auditee-dashboard/`),
		parent()
	]);
	const dashboard = await res.json();

	return {
		dashboard,
		title: user?.is_third_party ? m.myQuestionnaires() : m.auditDashboard()
	};
};
