import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';
import { BASE_API_URL } from '$lib/utils/constants';

const loginPageRegex = /^[a-zA-Z0-9]+:\/\/[^\/]+\/login\/?.*$/;

// get `locals.user` and pass it to the `page` store
export const load = loadFlash(async ({ locals, url, cookies, request, fetch }) => {
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
	if (locals.user) {
		try {
			const foldersRes = await fetch(`${BASE_API_URL}/folders/`);
			if (foldersRes.ok) {
				const data = await foldersRes.json();
				folders = data.results ?? data ?? [];
			}
		} catch (e) {
			console.error('Failed to fetch folders for focus mode:', e);
		}
	}

	return {
		user: locals.user,
		settings: locals.settings,
		featureflags: locals.featureflags,
		folders
	};
}) satisfies LayoutServerLoad;
