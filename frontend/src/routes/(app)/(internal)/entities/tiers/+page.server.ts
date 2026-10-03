import { BASE_API_URL } from '$lib/utils/constants';
import { error, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

const TIERS_ENDPOINT = `${BASE_API_URL}/tiers/`;

export const load: PageServerLoad = async ({ fetch }) => {
	const [res, fedByRes] = await Promise.all([
		fetch(`${TIERS_ENDPOINT}?ordering=-rank`),
		fetch(`${TIERS_ENDPOINT}fed-by/`)
	]);
	if (!res.ok) {
		error(res.status, 'Error loading tiers');
	}
	const data = await res.json();
	return {
		tiers: data.results ?? data,
		fedBy: fedByRes.ok ? await fedByRes.json() : []
	};
};

async function forward(fetch: typeof globalThis.fetch, url: string, init: RequestInit) {
	const res = await fetch(url, {
		...init,
		headers: { 'Content-Type': 'application/json' }
	});
	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		return fail(res.status, { error: body });
	}
	return { ok: true };
}

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const form = await request.formData();
		return forward(fetch, TIERS_ENDPOINT, {
			method: 'POST',
			body: JSON.stringify({
				name: form.get('name'),
				hexcolor: form.get('hexcolor') ?? ''
			})
		});
	},
	update: async ({ request, fetch }) => {
		const form = await request.formData();
		const id = form.get('id');
		const payload = JSON.parse(String(form.get('payload') ?? '{}'));
		return forward(fetch, `${TIERS_ENDPOINT}${id}/`, {
			method: 'PATCH',
			body: JSON.stringify(payload)
		});
	},
	remove: async ({ request, fetch }) => {
		const form = await request.formData();
		const res = await fetch(`${TIERS_ENDPOINT}${form.get('id')}/`, { method: 'DELETE' });
		if (!res.ok) {
			const body = await res.json().catch(() => ({}));
			return fail(res.status, { error: body });
		}
		return { ok: true };
	},
	reorder: async ({ request, fetch }) => {
		const form = await request.formData();
		return forward(fetch, `${TIERS_ENDPOINT}reorder/`, {
			method: 'POST',
			body: JSON.stringify({ ids: JSON.parse(String(form.get('ids') ?? '[]')) })
		});
	}
};
