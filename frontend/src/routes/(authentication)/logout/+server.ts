import { error, redirect, type Cookies } from '@sveltejs/kit';
import { ALLAUTH_API_URL, BASE_API_URL } from '$lib/utils/constants';
import { logger } from '$lib/server/logger';

type Fetch = typeof globalThis.fetch;

// `url` is the IdP logout URL, or null when the backend ended the SSO sessions
// and no IdP round-trip is needed.
type IdPLogoutResolution = { ok: true; url: string | null } | { ok: false };

// Resolved server-side so SSO logout keeps working when the API is not
// reachable from the browser (IP-restricted deployments).
async function resolveIdPLogoutUrl(fetch: Fetch, cookies: Cookies): Promise<IdPLogoutResolution> {
	const headers: Record<string, string> = {};
	const allauthSessionToken = cookies.get('allauth_session_token');
	const ssoSessionKey = cookies.get('sessionid');
	if (allauthSessionToken) headers['X-Allauth-Session-Token'] = allauthSessionToken;
	if (ssoSessionKey) headers['X-SSO-Session-Key'] = ssoSessionKey;

	try {
		const res = await fetch(`${BASE_API_URL}/iam/sso/logout-url/`, { method: 'POST', headers });
		if (!res.ok) throw new Error(`status ${res.status}`);
		const { logout_url } = await res.json();
		return { ok: true, url: typeof logout_url === 'string' && logout_url ? logout_url : null };
	} catch (error) {
		logger.error('Failed to resolve IdP logout URL', { error });
		return { ok: false };
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
	let target = '/login';

	const idpLogout = isSSOUser ? await resolveIdPLogoutUrl(fetch, cookies) : null;
	if (idpLogout?.ok) {
		if (idpLogout.url) target = idpLogout.url;
	} else {
		// Local user, or the SSO logout endpoint failed: end the allauth session
		// directly rather than clearing cookies over a session that is still alive.
		const res = await fetch(`${ALLAUTH_API_URL}/auth/session`, { method: 'DELETE' });
		const response = await res.json();
		if (response.meta?.is_authenticated !== false) {
			logger.error('Failed to end the allauth session', { status: res.status });
			error(400, 'Failed to end the session');
		}
	}

	cookies.delete('token', { path: '/' });
	cookies.delete('allauth_session_token', { path: '/' });
	cookies.delete('sessionid', { path: '/' });

	logger.info('User logged out', { user_id: locals.user?.id });

	// eslint-disable-next-line eslint-plugin-intuitem-sveltekit/secure-redirect -- backend-issued IdP URL
	redirect(302, target);
};
