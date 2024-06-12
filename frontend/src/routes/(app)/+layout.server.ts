import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';
import { setLanguageTag, sourceLanguageTag } from '$paraglide/runtime';

// get `locals.user` and pass it to the `page` store
export const load = loadFlash(async ({ locals, url, cookies }) => {
	if (!locals.user && !url.pathname.includes('/login')) {
		redirect(302, `/login?next=${url.pathname}`);
	}
	setLanguageTag(cookies.get('ciso_lang') || sourceLanguageTag);
	return { user: locals.user };
}) satisfies LayoutServerLoad;
