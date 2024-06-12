import { fail, redirect } from '@sveltejs/kit';
import { BASE_API_URL } from '$lib/utils/constants';

export const GET = async ({ locals }) => {
	if (!locals.user) {
		redirect(302, `/login?next=/home`);
	}
	redirect(302, '/bird-eye');
};

export const POST = async ({ fetch, cookies }) => {
	const requestInitOptions: RequestInit = {
		method: 'POST'
	};

	const endpoint = `${BASE_API_URL}/iam/logout/`;
	const res = await fetch(endpoint, requestInitOptions);

	if (!res.ok) {
		const response = await res.json();
		console.log(response);
		return fail(400, response.error);
	}

	cookies.delete('token', { path: '/' });

	redirect(302, '/login');
};
