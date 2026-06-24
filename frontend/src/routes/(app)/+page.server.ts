import { BASE_API_URL } from '$lib/utils/constants';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url, locals, fetch }) => {
	if (locals.user?.is_auditee) {
		redirect(302, '/auditee-dashboard');
	}
	// Landing mode: the user's own preference wins, else the admin global default.
	// 'analytics' | 'respondent' | 'portal'
	const landing = locals.user?.preferences?.ui?.landing || locals.settings?.default_landing;
	if (landing === 'portal' && locals.featureflags?.custom_portals) {
		const res = await fetch(`${BASE_API_URL}/portals/mine/`);
		const portals = res.ok ? await res.json() : [];
		if (portals.length) redirect(302, '/portal');
	}
	if (landing === 'respondent') {
		redirect(302, '/auditee-dashboard');
	}
	const queryParams = url.searchParams.has('refresh') ? '?refresh=1' : '';
	redirect(302, `/analytics${queryParams}`);
};
