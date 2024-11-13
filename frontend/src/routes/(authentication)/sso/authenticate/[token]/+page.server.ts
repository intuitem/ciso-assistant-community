import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals, params, cookies }) => {
	if (locals.user) {
		redirect(302, '/analytics');
	}

	cookies.set('token', params.token, {
		httpOnly: true,
		sameSite: 'lax',
		path: '/',
		secure: true
	});

	// User is logged in, now we need to fetch allauth's session token
	// to end the authentication flow
	const allauthSessionEndpoint = `${BASE_API_URL}/iam/session-token/`;
	const allauthSessionResponse = await fetch(allauthSessionEndpoint, { method: 'POST' });

	if (!allauthSessionResponse.ok) {
		console.error('Failed to fetch allauth session token');
		return fail(allauthSessionResponse.status);
	}

	const allauthSessionToken = await allauthSessionResponse.json().then((res) => res.token);

	cookies.set('allauth_session_token', allauthSessionToken, {
		httpOnly: true,
		sameSite: 'lax',
		path: '/',
		secure: true
	});

	redirect(302, '/analytics');
};
