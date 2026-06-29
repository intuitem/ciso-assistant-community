import { BASE_API_URL } from '$lib/utils/constants';
import { del, postJSON, unwrap } from '$lib/utils/portalApi';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.custom_portals) redirect(302, '/');
	const [p, pr] = await Promise.all([
		fetch(`${BASE_API_URL}/portals/`),
		fetch(`${BASE_API_URL}/portal-presets/`)
	]);
	return { portals: await unwrap(p), presets: await unwrap(pr) };
};

export const actions: Actions = {
	createPortal: async ({ request, fetch }) => {
		const data = await request.formData();
		const name = data.get('name') as string;
		if (!name?.trim()) return fail(400, { error: 'Name required' });
		const res = await postJSON(fetch, '/portals/', {
			name: name.trim(),
			is_public: data.get('visibility') === 'public'
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		redirect(303, `/portal-editor/${(await res.json()).id}`);
	},
	usePreset: async ({ request, fetch }) => {
		const preset = (await request.formData()).get('preset');
		const res = await postJSON(fetch, '/portals/from-preset/', { preset });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		redirect(303, `/portal-editor/${(await res.json()).id}`);
	},
	deletePortal: async ({ request, fetch }) => {
		const id = (await request.formData()).get('id');
		const res = await del(fetch, `/portals/${id}/`);
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	deletePreset: async ({ request, fetch }) => {
		const id = (await request.formData()).get('id');
		const res = await del(fetch, `/portal-presets/${id}/`);
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	}
};
