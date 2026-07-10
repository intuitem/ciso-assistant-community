import { BASE_API_URL } from '$lib/utils/constants';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const LINK_FIELDS = [
	'policies',
	'applied_controls',
	'task_templates',
	'processings',
	'filtering_labels'
] as const;

export const POST: RequestHandler = async ({ request, fetch, locals }) => {
	if (!locals.featureflags?.document_management) error(404, 'Not found');

	const fd = await request.formData();
	const source = String(fd.get('source') ?? 'author');
	const name = String(fd.get('name') ?? '');
	const document_type = String(fd.get('document_type') ?? 'policy');
	const folder = String(fd.get('folder') ?? '');
	const locale = String(fd.get('locale') ?? 'en');
	const classification = String(fd.get('classification') ?? '');
	const ref_id = String(fd.get('ref_id') ?? '');
	const links: Record<string, string[]> = {};
	for (const f of LINK_FIELDS) links[f] = fd.getAll(f).map(String);

	let res: Response;
	if (source === 'upload') {
		const file = fd.get('file');
		const out = new FormData();
		if (file instanceof File) out.append('file', file, file.name);
		out.append('name', name);
		out.append('document_type', document_type);
		out.append('folder', folder);
		out.append('locale', locale);
		res = await fetch(`${BASE_API_URL}/document-containers/upload/`, { method: 'POST', body: out });
	} else if (source === 'link') {
		res = await fetch(`${BASE_API_URL}/document-containers/link/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				url: String(fd.get('url') ?? ''),
				name,
				document_type,
				folder,
				locale
			})
		});
	} else {
		// Author: create the container; the editor's template picker seeds content.
		res = await fetch(`${BASE_API_URL}/document-containers/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				name,
				document_type,
				folder,
				...links,
				...(classification ? { classification } : {}),
				...(ref_id ? { ref_id } : {})
			})
		});
	}

	const data = await res.json().catch(() => null);
	if (!res.ok) return json(data ?? { error: 'Failed' }, { status: res.status });

	// upload/link go through custom actions that don't accept object-links or
	// classification — set them in a follow-up PATCH when present.
	if (
		source !== 'author' &&
		(classification || ref_id || LINK_FIELDS.some((f) => links[f].length))
	) {
		const patchRes = await fetch(`${BASE_API_URL}/document-containers/${data.id}/`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				...links,
				...(classification ? { classification } : {}),
				...(ref_id ? { ref_id } : {})
			})
		});
		if (!patchRes.ok) {
			return json(await patchRes.json().catch(() => ({ error: 'Failed to set links' })), {
				status: patchRes.status
			});
		}
	}
	return json(data);
};
