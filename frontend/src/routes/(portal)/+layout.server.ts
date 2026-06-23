import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';
import { BASE_API_URL } from '$lib/utils/constants';

export const load = loadFlash(async ({ locals, url, fetch }) => {
	if (!locals.user) {
		redirect(302, `/login?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
	if (!locals.featureflags?.custom_portals) {
		redirect(302, '/');
	}
	const res = await fetch(`${BASE_API_URL}/portals/mine/`);
	const portals: { id: string; name: string }[] = res.ok ? await res.json() : [];
	return {
		user: locals.user,
		settings: locals.settings,
		featureflags: locals.featureflags,
		portals
	};
}) satisfies LayoutServerLoad;
