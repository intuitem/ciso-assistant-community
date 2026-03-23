import { BASE_API_URL } from '$lib/utils/constants';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals, cookies }) => {
	if (locals.user) {
		redirect(302, locals.user.is_auditee ? '/auditee-dashboard' : '/analytics');
	}

	const token = cookies.get('token');
	if (!token) {
		redirect(302, '/login');
	}

	// User is logged in, now we need to fetch allauth's session token
	// to end the authentication flow
	const allauthSessionEndpoint = `${BASE_API_URL}/iam/session-token/`;
	const allauthSessionResponse = await fetch(allauthSessionEndpoint, { method: 'POST' });

	if (!allauthSessionResponse.ok) {
		console.error('Failed to fetch allauth session token:', allauthSessionResponse.status);
		redirect(302, '/login');
	}

	const allauthSessionToken = await allauthSessionResponse.json().then((res) => res.token);

	if (!allauthSessionToken || typeof allauthSessionToken !== 'string') {
		console.error('Session token response missing or invalid token field');
		redirect(302, '/login');
	}

	cookies.set('allauth_session_token', allauthSessionToken, {
		httpOnly: true,
		sameSite: 'lax',
		path: '/',
		secure: true
	});

	redirect(302, '/');
};
