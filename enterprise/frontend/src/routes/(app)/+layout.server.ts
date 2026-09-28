import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

import { BASE_API_URL } from '$lib/utils/constants';
import { env } from '$env/dynamic/public';

const loginPageRegex = /^[a-zA-Z0-9]+:\/\/[^\/]+\/login\/?.*$/;

export const load = loadFlash(async ({ fetch, locals, url, cookies, request }) => {
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

	// Fetch accessible folder tree for Focus Mode selector
	let orgTree: {
		name: string;
		uuid: string | null;
		viewable?: boolean;
		children?: unknown[];
	} | null = null;
	const focusModeEnabled = featureflags?.focus_mode ?? false;
	if (user && focusModeEnabled) {
		try {
			const treeRes = await fetch(
				`${BASE_API_URL}/folders/org_tree/?include_perimeters=false&no_focus=true`
			);
			if (treeRes.ok) {
				orgTree = await treeRes.json();
			}
		} catch (e) {
			console.error('Failed to fetch folder tree for focus mode:', e);
		}
	}

	let licenseStatus = {};
	try {
		const licenseRes = await fetch(`${BASE_API_URL}/license-status/`);
		if (licenseRes.ok) {
			licenseStatus = await licenseRes.json();
		} else {
			console.error('Failed to fetch license status:', licenseRes.status, licenseRes.statusText);
		}
	} catch (e) {
		console.error('Error fetching license status:', e);
	}
	const LICENSE_EXPIRATION_NOTIFY_DAYS = Object.hasOwn(env, 'PUBLIC_LICENSE_EXPIRATION_NOTIFY_DAYS')
		? env.PUBLIC_LICENSE_EXPIRATION_NOTIFY_DAYS
		: 7;

	const LICENSE_EXPIRATION_MESSAGE = Object.hasOwn(env, 'PUBLIC_LICENSE_EXPIRATION_MESSAGE')
		? env.PUBLIC_LICENSE_EXPIRATION_MESSAGE
		: '';

	return {
		user,
		settings,
		featureflags,
		licenseStatus,
		LICENSE_EXPIRATION_NOTIFY_DAYS,
		LICENSE_EXPIRATION_MESSAGE,
		orgTree
	};
}) satisfies LayoutServerLoad;
