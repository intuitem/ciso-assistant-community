import { BASE_API_URL } from '$lib/utils/constants';
import { error, fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch, locals }) => {
	if (!locals.featureflags?.custom_portals) redirect(302, '/');
	const res = await fetch(`${BASE_API_URL}/portals/${params.id}/`);
	if (!res.ok) error(res.status === 404 ? 404 : 500, 'Portal not found');
	return { portal: await res.json() };
};

async function patch(fetch: typeof globalThis.fetch, id: string, body: unknown) {
	return fetch(`${BASE_API_URL}/portals/${id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

export const actions: Actions = {
	saveContent: async ({ params, request, fetch }) => {
		const payload = (await request.formData()).get('payload') as string;
		const res = await patch(fetch, params.id!, { content: JSON.parse(payload) });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	updateMeta: async ({ params, request, fetch }) => {
		const data = await request.formData();
		const res = await patch(fetch, params.id!, {
			name: (data.get('name') as string)?.trim(),
			description: (data.get('description') as string) ?? ''
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	setStatus: async ({ params, request, fetch }) => {
		const status = (await request.formData()).get('status');
		const res = await patch(fetch, params.id!, { status });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	duplicate: async ({ params, fetch }) => {
		const res = await fetch(`${BASE_API_URL}/portals/${params.id}/duplicate/`, { method: 'POST' });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		redirect(303, `/portal-editor/${(await res.json()).id}`);
	}
};
