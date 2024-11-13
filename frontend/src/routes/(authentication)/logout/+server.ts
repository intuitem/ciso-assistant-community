import { fail, redirect } from '@sveltejs/kit';
import { ALLAUTH_API_URL, BASE_API_URL } from '$lib/utils/constants';

export const GET = async ({ locals }) => {
	if (!locals.user) {
		redirect(302, `/login?next=/home`);
	}
	redirect(302, '/analytics');
};

export const POST = async ({ fetch, cookies }) => {
	const requestInitOptions: RequestInit = {
		method: 'DELETE'
	};

	const endpoint = `${ALLAUTH_API_URL}/auth/session`;
	const res = await fetch(endpoint, requestInitOptions);

	const response = await res.json();
	if (response.meta.is_authenticated !== false) return fail(400, response.error);

	cookies.delete('token', { path: '/' });
	cookies.delete('allauth_session_token', { path: '/' });

	redirect(302, '/login');
};
