import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

const loginPageRegex = /^[a-zA-Z0-9]+:\/\/[^\/]+\/login\/?.*$/;

// Resolve the session and app config, and pass them to the `page` store.
export const load = loadFlash(async ({ locals, url, cookies, request }) => {
	const user = await locals.getUser();
	if (!user && !url.pathname.includes('/login')) {
		redirect(302, `/login?next=${url.pathname}`);
	}

	const [settings, featureflags] = await Promise.all([
		locals.getSettings(),
		locals.getFeatureFlags()
	]);

	if (
		user &&
		settings?.enforce_mfa &&
		!user.has_mfa_enabled &&
		!user.is_superuser &&
		user.is_local &&
		!user.is_sso &&
		!url.pathname.startsWith('/setup-mfa')
	) {
		redirect(302, '/setup-mfa');
	}

	if (user) {
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
	return { user, settings, featureflags };
}) satisfies LayoutServerLoad;
