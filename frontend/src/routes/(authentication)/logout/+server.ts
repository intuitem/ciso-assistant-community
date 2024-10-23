import { fail, redirect } from '@sveltejs/kit';
import { BASE_API_URL } from '$lib/utils/constants';

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

	const endpoint = `${BASE_API_URL}/_allauth/app/v1/auth/session`;
	const res = await fetch(endpoint, requestInitOptions);

	const response = await res.json();
	if (response.meta.is_authenticated !== false) return fail(400, response.error);

	cookies.delete('token', { path: '/' });
	cookies.delete('allauth_session_token', { path: '/' });

	redirect(302, '/login');
};
