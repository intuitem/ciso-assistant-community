import { BASE_API_URL } from '#lib/utils/constants.js';
import { error, fail, type NumericRange } from '@sveltejs/kit';
import { message, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { z } from 'zod';
import { m } from '#paraglide/messages.js';
import type { Actions, PageServerLoad } from './$types';

const ENDPOINT = `${BASE_API_URL}/iam/connected-apps`;
const idSchema = z.object({ id: z.string() });
const PAGE_SIZE = 20;

export const load: PageServerLoad = async ({ fetch, url }) => {
	const search = url.searchParams.get('search') ?? '';
	const parsed = parseInt(url.searchParams.get('page') ?? '1');
	const pageNumber = Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
	const params = new URLSearchParams({
		limit: String(PAGE_SIZE),
		offset: String((pageNumber - 1) * PAGE_SIZE)
	});
	if (search) params.set('search', search);

	const res = await fetch(`${ENDPOINT}/all/?${params}`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, m.connectedAppsLoadError());
	}
	const { count, results } = await res.json();
	return {
		title: m.connectedApps(),
		connections: results,
		search,
		pageNumber,
		pageCount: Math.max(1, Math.ceil(count / PAGE_SIZE))
	};
};

export const actions: Actions = {
	revoke: async (event) => {
		const form = await superValidate(await event.request.formData(), zod(idSchema));
		if (!form.valid) return fail(400, { form });
		// one hidden id per modal: "<user id>:<client id>"
		const [userId, clientId] = form.data.id.split(':');
		const response = await event.fetch(
			`${ENDPOINT}/all/${encodeURIComponent(userId)}/${encodeURIComponent(clientId)}/`,
			{ method: 'DELETE' }
		);
		if (!response.ok) return fail(response.status, { form });
		setFlash({ type: 'success', message: m.connectedAppRevoked() }, event);
		return message(form, { status: response.status });
	},
	revokeGroup: async (event) => {
		const form = await superValidate(await event.request.formData(), zod(idSchema));
		if (!form.valid) return fail(400, { form });
		const response = await event.fetch(`${ENDPOINT}/apps/${encodeURIComponent(form.data.id)}/`, {
			method: 'DELETE'
		});
		if (!response.ok) return fail(response.status, { form });
		const { users } = await response.json();
		setFlash({ type: 'success', message: m.connectedAppRevokedForEveryone({ users }) }, event);
		return message(form, { status: response.status });
	}
};
