import { BASE_API_URL } from '$lib/utils/constants';
import { SnapshotCreateSchema, SnapshotEditSchema } from '$lib/utils/schemas';
import { error, fail, redirect, type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

const unwrap = async (res: Response) => {
	if (!res.ok) error(res.status, await res.text());
	const data = await res.json();
	return data.results ?? data;
};

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.custom_portals) redirect(302, '/');
	const [snaps, audits] = await Promise.all([
		fetch(`${BASE_API_URL}/framework-snapshots/`),
		fetch(`${BASE_API_URL}/compliance-assessments/`)
	]);
	return {
		snapshots: await unwrap(snaps),
		audits: await unwrap(audits),
		createForm: await superValidate(zod(SnapshotCreateSchema)),
		editForm: await superValidate(zod(SnapshotEditSchema))
	};
};

const postJSON = (fetch: typeof globalThis.fetch, path: string, body: unknown) =>
	fetch(`${BASE_API_URL}${path}`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(SnapshotCreateSchema));
		if (!form.valid) return fail(400, { form });
		const res = await postJSON(fetch, '/framework-snapshots/', {
			name: form.data.name,
			source_audit: form.data.source_audit,
			folder: form.data.folder,
			implementation_groups: (form.data.implementation_groups ?? []).filter(Boolean)
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { form };
	},
	update: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(SnapshotEditSchema));
		if (!form.valid) return fail(400, { form });
		const patch = await fetch(`${BASE_API_URL}/framework-snapshots/${form.data.id}/`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				name: form.data.name,
				implementation_groups: (form.data.implementation_groups ?? []).filter(Boolean),
				display_mode: form.data.display_mode
			})
		});
		if (!patch.ok) return fail(patch.status, { error: await patch.text() });
		// Re-sync so an implementation-group change is reflected in the captured data.
		await postJSON(fetch, `/framework-snapshots/${form.data.id}/sync/`, {});
		return { form };
	},
	preview: async ({ request, fetch }) => {
		const id = (await request.formData()).get('id');
		const snapRes = await fetch(`${BASE_API_URL}/framework-snapshots/${id}/`);
		if (!snapRes.ok) return fail(snapRes.status, { error: await snapRes.text() });
		const snap = await snapRes.json();
		const res = await postJSON(fetch, '/framework-snapshots/preview/', {
			source_audit: snap.source_audit?.id,
			implementation_groups: snap.implementation_groups ?? []
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		const preview = await res.json();
		return {
			diff: {
				id,
				name: snap.name,
				current: snap.summary ?? {},
				next: preview.summary ?? {},
				controlsCurrent: snap.control_count ?? 0,
				controlsNext: (preview.control_ids ?? []).length
			}
		};
	},
	sync: async ({ request, fetch }) => {
		const id = (await request.formData()).get('id');
		const res = await postJSON(fetch, `/framework-snapshots/${id}/sync/`, {});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	delete: async ({ request, fetch }) => {
		const id = (await request.formData()).get('id');
		const res = await fetch(`${BASE_API_URL}/framework-snapshots/${id}/`, { method: 'DELETE' });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	}
};
