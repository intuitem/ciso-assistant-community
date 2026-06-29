import { BASE_API_URL } from '$lib/utils/constants';
import { patchJSON, unwrap } from '$lib/utils/portalApi';
import { PortalSettingsSchema } from '$lib/utils/schemas';
import { error, fail, redirect, type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch, locals }) => {
	if (!locals.featureflags?.custom_portals) redirect(302, '/');
	const res = await fetch(`${BASE_API_URL}/portals/${params.id}/`);
	if (!res.ok) error(res.status === 404 ? 404 : 500, 'Portal not found');
	const portal = await res.json();
	const [publicDocuments, snapshots, rawFrameworks, rawFolders] = await Promise.all([
		fetch(`${BASE_API_URL}/public-documents/`).then(unwrap),
		fetch(`${BASE_API_URL}/framework-snapshots/`).then(unwrap),
		fetch(`${BASE_API_URL}/frameworks/`).then(unwrap),
		fetch(`${BASE_API_URL}/folders/?content_type=DO`).then(unwrap)
	]);
	const frameworks = rawFrameworks.map((f: any) => ({
		id: f.id,
		name: f.name,
		implementation_groups_definition: f.implementation_groups_definition ?? [],
		effective_field_visibility: f.effective_field_visibility ?? null
	}));
	const folders = rawFolders.map((f: any) => ({ id: f.id, name: f.name }));
	const settingsForm = await superValidate(
		{
			enabled: portal.enabled,
			is_default: portal.is_default,
			order: portal.order,
			audience_groups: (portal.audience_groups ?? []).map((g: { id: string }) => g.id),
			is_public: portal.is_public,
			is_primary: portal.is_primary,
			branding: portal.branding ?? {}
		},
		zod(PortalSettingsSchema)
	);
	return { portal, settingsForm, publicDocuments, snapshots, frameworks, folders };
};

const patchPortal = (fetch: typeof globalThis.fetch, id: string, body: unknown) =>
	patchJSON(fetch, `/portals/${id}/`, body);

export const actions: Actions = {
	uploadDocument: async ({ request, fetch }) => {
		const data = await request.formData();
		const file = data.get('file');
		if (!(file instanceof File) || file.size === 0) return fail(400, { error: 'File required' });
		const name = ((data.get('name') as string) || '').trim() || file.name;
		const folder = data.get('folder') as string;
		const body = new FormData();
		body.append('name', name);
		body.append('file', file);
		if (folder) body.append('folder', folder);
		const res = await fetch(`${BASE_API_URL}/public-documents/`, { method: 'POST', body });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		const doc = await res.json();
		return { uploaded: { id: doc.id, name: doc.name, token: doc.token } };
	},
	saveContent: async ({ params, request, fetch }) => {
		const payload = (await request.formData()).get('payload') as string;
		let content;
		try {
			content = JSON.parse(payload);
		} catch {
			return fail(400, { error: 'Invalid payload' });
		}
		const res = await patchPortal(fetch, params.id!, { content });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	updateMeta: async ({ params, request, fetch }) => {
		const name = ((await request.formData()).get('name') as string)?.trim();
		if (!name) return fail(400, { error: 'Name required' });
		const res = await patchPortal(fetch, params.id!, { name });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	setStatus: async ({ params, request, fetch }) => {
		const status = (await request.formData()).get('status');
		const res = await patchPortal(fetch, params.id!, { status });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	updateSettings: async ({ params, request, fetch }) => {
		const form = await superValidate(request, zod(PortalSettingsSchema));
		if (!form.valid) return fail(400, { form });
		const body: Record<string, unknown> = {
			enabled: form.data.enabled,
			is_default: form.data.is_default,
			order: form.data.order,
			audience_groups: form.data.audience_groups ?? [],
			is_public: form.data.is_public,
			is_primary: form.data.is_primary
		};
		// Branding is only authored on public portals; omit it otherwise so saving an
		// internal portal's settings can't wipe branding set while it was public.
		if (form.data.is_public) body.branding = form.data.branding ?? {};
		const res = await patchPortal(fetch, params.id!, body);
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { form };
	},
	regeneratePublicToken: async ({ params, fetch }) => {
		const res = await fetch(`${BASE_API_URL}/portals/${params.id}/regenerate-public-token/`, {
			method: 'POST'
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	duplicate: async ({ params, fetch }) => {
		const res = await fetch(`${BASE_API_URL}/portals/${params.id}/duplicate/`, { method: 'POST' });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		redirect(303, `/portal-editor/${(await res.json()).id}`);
	}
};
