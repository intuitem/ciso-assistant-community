import { fail, redirect, type Cookies } from '@sveltejs/kit';
import { ALLAUTH_API_URL, BASE_API_URL } from '$lib/utils/constants';
import { logger } from '$lib/server/logger';

// Resolved server-side so SSO logout keeps working when the API is not
// reachable from the browser (IP-restricted deployments).
async function getSSOLogoutUrl(fetch: typeof globalThis.fetch, cookies: Cookies): Promise<string> {
	const headers: Record<string, string> = {};
	const allauthSessionToken = cookies.get('allauth_session_token');
	const ssoSessionKey = cookies.get('sessionid');
	if (allauthSessionToken) headers['X-Allauth-Session-Token'] = allauthSessionToken;
	if (ssoSessionKey) headers['X-SSO-Session-Key'] = ssoSessionKey;

	try {
		const res = await fetch(`${BASE_API_URL}/iam/sso/logout-url/`, { method: 'POST', headers });
		if (!res.ok) {
			logger.error('Failed to resolve SSO logout URL', { status: res.status });
			return '/login';
		}
		const logoutUrl = await res.json().then((data) => data.logout_url);
		return typeof logoutUrl === 'string' && logoutUrl ? logoutUrl : '/login';
	} catch (error) {
		logger.error('Failed to resolve SSO logout URL', { error });
		return '/login';
	}
}

export const GET = async ({ locals }) => {
	if (!locals.user) {
		redirect(302, `/login?next=/home`);
	}
	redirect(302, '/analytics');
};

export const POST = async ({ fetch, cookies, locals }) => {
	const isSSOUser = locals.user?.is_sso === true;

	if (isSSOUser) {
		const logoutUrl = await getSSOLogoutUrl(fetch, cookies);

		cookies.delete('token', { path: '/' });
		cookies.delete('allauth_session_token', { path: '/' });
		cookies.delete('sessionid', { path: '/' });

		logger.info('User logged out', { user_id: locals.user?.id });

		// eslint-disable-next-line eslint-plugin-intuitem-sveltekit/secure-redirect -- backend-issued IdP URL
		redirect(302, logoutUrl);
	}

	const requestInitOptions: RequestInit = {
		method: 'DELETE'
	};

	const endpoint = `${ALLAUTH_API_URL}/auth/session`;
	const res = await fetch(endpoint, requestInitOptions);

	const response = await res.json();
	if (response.meta.is_authenticated !== false) return fail(400, response.error);

	cookies.delete('token', { path: '/' });
	cookies.delete('allauth_session_token', { path: '/' });

	logger.info('User logged out', { user_id: locals.user?.id });

	redirect(302, '/login');
};
