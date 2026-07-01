import { BASE_API_URL } from '$lib/utils/constants';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url, locals }) => {
	if (locals.featureflags?.document_management === false) {
		redirect(302, '/');
	}

	const containerRes = await fetch(`${BASE_API_URL}/document-containers/${params.id}/`);
	if (!containerRes.ok) error(404, 'Document not found');
	const container = await containerRes.json();

	const docsRes = await fetch(`${BASE_API_URL}/managed-documents/?container=${params.id}`);
	const docsJson = docsRes.ok ? await docsRes.json() : {};
	const docs: any[] = docsJson.results ?? (Array.isArray(docsJson) ? docsJson : []);

	const requested = url.searchParams.get('doc');
	const selected =
		docs.find((d) => d.id === requested) ?? docs.find((d) => d.default_locale) ?? docs[0] ?? null;

	let content = '';
	let revision: any = null;
	if (selected?.current_revision?.id) {
		const revRes = await fetch(
			`${BASE_API_URL}/document-revisions/${selected.current_revision.id}/`
		);
		if (revRes.ok) {
			revision = await revRes.json();
			content = revision.content ?? '';
		}
	}

	return { container, docs, selected, content, revision };
};
