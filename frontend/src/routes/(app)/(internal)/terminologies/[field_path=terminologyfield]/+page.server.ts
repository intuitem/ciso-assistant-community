import { BASE_API_URL } from '#lib/utils/constants.js';
import { safeTranslate } from '#lib/utils/i18n.js';
import { fetchAllPages } from '#lib/utils/pagination.js';
import { TERMINOLOGY_FIELDS, type TerminologyField } from '#lib/utils/terminology-fields.js';
import { error, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

const ENDPOINT = `${BASE_API_URL}/terminologies/`;

export const load: PageServerLoad = async ({ fetch, params }) => {
	const fieldPath = params.field_path as TerminologyField;
	const terminologies = await fetchAllPages(
		fetch,
		`${ENDPOINT}?field_path=${encodeURIComponent(fieldPath)}&ordering=order,name`
	).catch((e) => error(e.status ?? 500, 'Error loading terminologies'));
	return {
		fieldPath,
		terminologies,
		title: safeTranslate(TERMINOLOGY_FIELDS[fieldPath])
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
	create: async ({ request, fetch, params }) => {
		const form = await request.formData();
		return forward(fetch, ENDPOINT, {
			method: 'POST',
			body: JSON.stringify({
				name: form.get('name'),
				hexcolor: form.get('hexcolor') ?? '',
				field_path: params.field_path
			})
		});
	},
	update: async ({ request, fetch }) => {
		const form = await request.formData();
		const payload = JSON.parse(String(form.get('payload') ?? '{}'));
		return forward(fetch, `${ENDPOINT}${form.get('id')}/`, {
			method: 'PATCH',
			body: JSON.stringify(payload)
		});
	},
	remove: async ({ request, fetch }) => {
		const form = await request.formData();
		const res = await fetch(`${ENDPOINT}${form.get('id')}/`, { method: 'DELETE' });
		if (!res.ok) {
			const body = await res.json().catch(() => ({}));
			return fail(res.status, { error: body });
		}
		return { ok: true };
	},
	reorder: async ({ request, fetch, params }) => {
		const form = await request.formData();
		return forward(fetch, `${ENDPOINT}reorder/`, {
			method: 'POST',
			body: JSON.stringify({
				field_path: params.field_path,
				ids: JSON.parse(String(form.get('ids') ?? '[]'))
			})
		});
	}
};
