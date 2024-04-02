import { fail, redirect } from '@sveltejs/kit';
import { BASE_API_URL } from '$lib/utils/constants';
import { base } from '$app/paths';

export const GET = async ({ locals }) => {
	if (!locals.user) {
		redirect(302, `${base}/login?next=/home`);
		// TODO: why /home?
	}
	redirect(302, `${base}/analytics`);
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

	cookies.delete('sessionid', { path: '/' });

	redirect(302, `${base}/login`);
};
