import { redirect, type Cookies } from '@sveltejs/kit';
import { ALLAUTH_API_URL, BASE_API_URL } from '$lib/utils/constants';
import { logger } from '$lib/server/logger';

type Fetch = typeof globalThis.fetch;

// A logout leg must never hang: the IdP discovery call behind logout-url/ can
// stall, and a dead-end here leaves the user logged in.
const LOGOUT_CALL_TIMEOUT_MS = 10_000;

// `url` is the IdP logout URL, or null when no IdP round-trip is needed.
type IdPLogoutResolution =
	{ ok: true; url: string | null; allauthSessionEnded: boolean } | { ok: false };

// Resolved server-side so SSO logout keeps working when the API is not
// reachable from the browser (IP-restricted deployments).
async function resolveIdPLogoutUrl(fetch: Fetch, cookies: Cookies): Promise<IdPLogoutResolution> {
	const headers: Record<string, string> = {};
	const allauthSessionToken = cookies.get('allauth_session_token');
	const ssoSessionKey = cookies.get('sessionid');
	if (allauthSessionToken) headers['X-Allauth-Session-Token'] = allauthSessionToken;
	if (ssoSessionKey) headers['X-SSO-Session-Key'] = ssoSessionKey;

	try {
		const res = await fetch(`${BASE_API_URL}/iam/sso/logout-url/`, {
			method: 'POST',
			headers,
			signal: AbortSignal.timeout(LOGOUT_CALL_TIMEOUT_MS)
		});
		if (!res.ok) throw new Error(`status ${res.status}`);
		const { logout_url, allauth_session_ended } = await res.json();
		return {
			ok: true,
			url: typeof logout_url === 'string' && logout_url ? logout_url : null,
			allauthSessionEnded: allauth_session_ended === true
		};
	} catch (error) {
		logger.error('Failed to resolve IdP logout URL', { error });
		return { ok: false };
	}
}

// Best-effort: the browser is signed out either way, so a failure here must
// never strand the user with their cookies still set.
async function endAllauthSession(fetch: Fetch): Promise<boolean> {
	try {
		const res = await fetch(`${ALLAUTH_API_URL}/auth/session`, {
			method: 'DELETE',
			signal: AbortSignal.timeout(LOGOUT_CALL_TIMEOUT_MS)
		});
		const { meta } = await res.json();
		if (meta?.is_authenticated === false) return true;
		logger.error('Failed to end the allauth session', { status: res.status });
	} catch (error) {
		logger.error('Failed to end the allauth session', { error });
	}
	return false;
}

// Nothing else in the logout flow revokes it: allauth ends the Django session,
// not the token, so a captured token would stay valid for its whole TTL.
async function revokeAccessToken(fetch: Fetch): Promise<boolean> {
	try {
		const res = await fetch(`${BASE_API_URL}/iam/logout/`, {
			method: 'POST',
			signal: AbortSignal.timeout(LOGOUT_CALL_TIMEOUT_MS)
		});
		if (res.ok) return true;
		logger.error('Failed to revoke the access token', { status: res.status });
	} catch (error) {
		logger.error('Failed to revoke the access token', { error });
	}
	return false;
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
	if (idpLogout?.ok && idpLogout.url) target = idpLogout.url;

	// A 200 from logout-url/ is not proof the allauth session is gone: it only
	// ends the sessions whose keys it was given and whose owner is the caller.
	if (!idpLogout?.ok || !idpLogout.allauthSessionEnded) {
		await endAllauthSession(fetch);
	}

	// Last, since the calls above authenticate with it.
	await revokeAccessToken(fetch);

	cookies.delete('token', { path: '/' });
	cookies.delete('allauth_session_token', { path: '/' });
	cookies.delete('sessionid', { path: '/' });

	logger.info('User logged out', { user_id: locals.user?.id });

	// eslint-disable-next-line eslint-plugin-intuitem-sveltekit/secure-redirect -- backend-issued IdP URL
	redirect(302, target);
};
