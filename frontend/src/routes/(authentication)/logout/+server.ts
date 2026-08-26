import { fail, redirect } from '@sveltejs/kit';
import { ALLAUTH_API_URL, BACKEND_API_EXPOSED_URL } from '$lib/utils/constants';
import { logger } from '$lib/server/logger';

export const GET = async ({ locals }) => {
	if (!locals.user) {
		redirect(302, `/login?next=/home`);
	}
	redirect(302, '/analytics');
};

export const POST = async ({ fetch, cookies, locals }) => {
	const isSSOUser = locals.user?.is_sso === true;

	if (isSSOUser) {
		cookies.delete('token', { path: '/' });

		logger.info('User logged out', { user_id: locals.user?.id });

		// Preserve the Django session until the SLO endpoint consumes it.
		redirect(302, `${BACKEND_API_EXPOSED_URL}/iam/sso/logout/`);
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
