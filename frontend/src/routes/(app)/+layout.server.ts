import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';
import { setLocale } from '$paraglide/runtime';
import { DEFAULT_LANGUAGE } from '$lib/utils/constants';

const loginPageRegex = /^[a-zA-Z0-9]+:\/\/[^\/]+\/login\/?.*$/;

// get `locals.user` and pass it to the `page` store
export const load = loadFlash(async ({ locals, url, cookies, request }) => {
	if (!locals.user && !url.pathname.includes('/login')) {
		redirect(302, `/login?next=${url.pathname}`);
	} else {
		const referer = request.headers.get('referer') ?? '';
		const fromLogin = loginPageRegex.test(referer);
		if (fromLogin) {
			cookies.set('from_login', 'true', {
				httpOnly: false,
				sameSite: 'lax',
				path: '/',
				secure: true
			});
		}
	}
	setLocale(cookies.get('PARAGLIDE_LOCALE') || DEFAULT_LANGUAGE);
	return { user: locals.user, settings: locals.settings };
}) satisfies LayoutServerLoad;
