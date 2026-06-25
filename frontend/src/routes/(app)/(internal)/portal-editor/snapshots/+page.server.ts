import { BASE_API_URL } from '$lib/utils/constants';
import { error, fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const unwrap = async (res: Response) => {
	if (!res.ok) error(res.status, await res.text());
	const data = await res.json();
	return data.results ?? data;
};

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.custom_portals) redirect(302, '/');
	const [snaps, audits, folders] = await Promise.all([
		fetch(`${BASE_API_URL}/framework-snapshots/`),
		fetch(`${BASE_API_URL}/compliance-assessments/`),
		fetch(`${BASE_API_URL}/folders/`)
	]);
	return {
		snapshots: await unwrap(snaps),
		audits: await unwrap(audits),
		folders: await unwrap(folders)
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
		const data = await request.formData();
		const name = (data.get('name') as string)?.trim();
		const source_audit = data.get('source_audit') as string;
		const folder = data.get('folder') as string;
		const igs = ((data.get('implementation_groups') as string) || '')
			.split(',')
			.map((s) => s.trim())
			.filter(Boolean);
		if (!name || !source_audit) return fail(400, { error: 'Name and audit required' });
		const res = await postJSON(fetch, '/framework-snapshots/', {
			name,
			source_audit,
			folder,
			implementation_groups: igs
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
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
