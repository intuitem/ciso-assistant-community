import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

import { BASE_API_URL } from '$lib/utils/constants';
import { env } from '$env/dynamic/public';

const loginPageRegex = /^[a-zA-Z0-9]+:\/\/[^\/]+\/login\/?.*$/;

// get `locals.user` and pass it to the `page` store
export const load = loadFlash(async ({ fetch, locals, url, cookies, request }) => {
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

	// Fetch accessible folders for Focus Mode selector
	let folders: { id: string; str: string; name: string; content_type: string }[] = [];
	const focusModeEnabled = locals.featureflags?.focus_mode ?? false;
	if (locals.user && focusModeEnabled) {
		try {
			const foldersRes = await fetch(`${BASE_API_URL}/folders?no_focus=true`);
			if (foldersRes.ok) {
				const data = await foldersRes.json();
				folders = data.results ?? data ?? [];
			}
		} catch (e) {
			console.error('Failed to fetch folders for focus mode:', e);
		}
	}

	const licenseStatus = await fetch(`${BASE_API_URL}/license-status/`).then((res) => res.json());
	const LICENSE_EXPIRATION_NOTIFY_DAYS = Object.hasOwn(env, 'PUBLIC_LICENSE_EXPIRATION_NOTIFY_DAYS')
		? env.PUBLIC_LICENSE_EXPIRATION_NOTIFY_DAYS
		: 7;

	return {
		user: locals.user,
		settings: locals.settings,
		featureflags: locals.featureflags,
		licenseStatus,
		LICENSE_EXPIRATION_NOTIFY_DAYS,
		folders
	};
}) satisfies LayoutServerLoad;
