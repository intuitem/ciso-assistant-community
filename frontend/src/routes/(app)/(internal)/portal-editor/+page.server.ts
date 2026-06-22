import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const unwrap = async (res: Response) => {
	if (!res.ok) return [];
	const data = await res.json();
	return data.results ?? data;
};

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.custom_portals) redirect(302, '/');
	const [p, pr] = await Promise.all([
		fetch(`${BASE_API_URL}/portals/`),
		fetch(`${BASE_API_URL}/portal-presets/`)
	]);
	return { portals: await unwrap(p), presets: await unwrap(pr) };
};

async function postJSON(fetch: typeof globalThis.fetch, path: string, body: unknown) {
	return fetch(`${BASE_API_URL}${path}`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

export const actions: Actions = {
	createPortal: async ({ request, fetch }) => {
		const name = (await request.formData()).get('name') as string;
		if (!name?.trim()) return fail(400, { error: 'Name required' });
		const res = await postJSON(fetch, '/portals/', { name: name.trim() });
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
		const res = await fetch(`${BASE_API_URL}/portals/${id}/`, { method: 'DELETE' });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	deletePreset: async ({ request, fetch }) => {
		const id = (await request.formData()).get('id');
		const res = await fetch(`${BASE_API_URL}/portal-presets/${id}/`, { method: 'DELETE' });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	}
};
