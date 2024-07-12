import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, params, cookies }) => {
	if (locals.user) {
		redirect(302, '/analytics');
	}

	cookies.set('token', params.token, {
		httpOnly: true,
		sameSite: 'lax',
		path: '/',
		secure: true
	});

	redirect(302, '/analytics');
};
