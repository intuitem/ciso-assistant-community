import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';
import { BASE_API_URL } from '$lib/utils/constants';

export const load = loadFlash(async ({ locals, url, fetch }) => {
	const user = await locals.getUser();
	if (!user) {
		redirect(302, `/login?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
	const [settings, featureflags] = await Promise.all([
		locals.getSettings(),
		locals.getFeatureFlags()
	]);
	if (!featureflags?.custom_portals) {
		redirect(302, '/');
	}
	const res = await fetch(`${BASE_API_URL}/portals/mine/`);
	const portals: { id: string; name: string; is_default: boolean }[] = res.ok
		? await res.json()
		: [];
	return {
		user,
		settings,
		featureflags,
		portals
	};
}) satisfies LayoutServerLoad;
