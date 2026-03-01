import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

const loginPageRegex = /^[a-zA-Z0-9]+:\/\/[^\/]+\/login\/?.*$/;

// get `locals.user` and pass it to the `page` store
export const load = loadFlash(async ({ locals, url, cookies, request }) => {
	if (!locals.user && !url.pathname.includes('/login')) {
		redirect(302, `/login?next=${url.pathname}`);
	}

	if (
		locals.user &&
		locals.settings?.enforce_mfa &&
		!locals.user.has_mfa_enabled &&
		!locals.user.is_superuser &&
		locals.user.is_local &&
		!url.pathname.startsWith('/setup-mfa')
	) {
		redirect(302, '/setup-mfa');
	}

	if (locals.user) {
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
	return { user: locals.user, settings: locals.settings, featureflags: locals.featureflags };
}) satisfies LayoutServerLoad;
