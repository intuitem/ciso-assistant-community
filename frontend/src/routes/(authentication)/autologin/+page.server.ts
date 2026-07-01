import { getSecureRedirect } from '$lib/utils/helpers';
import { BASE_API_URL } from '$lib/utils/constants';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals, url }) => {
	// Already authenticated → straight to the app
	if (locals.user) {
		redirect(302, locals.user.is_auditee ? '/auditee-dashboard' : '/analytics');
	}

	const SSOInfo = await fetch(`${BASE_API_URL}/settings/sso/info/`).then((res) => res.json());

	// SSO not enabled → fall back to the regular login page
	if (!SSOInfo?.is_enabled) {
		redirect(302, '/login');
	}

	const next = getSecureRedirect(url.searchParams.get('next')) || '/';

	return { SSOInfo, next };
};
