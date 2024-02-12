import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

// get `locals.user` and pass it to the `page` store
export const load = loadFlash(async ({ locals, url }) => {
	if (!locals.user && !url.pathname.includes('/login')) {
		redirect(302, `/login?next=${url.pathname}`);
	}
	return { user: locals.user };
}) satisfies LayoutServerLoad;
