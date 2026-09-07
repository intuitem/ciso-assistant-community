import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url, locals }) => {
	if (!locals.featureflags?.document_management) {
		redirect(302, '/');
	}

	const containerRes = await fetch(`${BASE_API_URL}/document-containers/${params.id}/`);
	if (!containerRes.ok) error(404, 'Document not found');
	const container = await containerRes.json();

	const docs: any[] = await fetchAllPages(
		fetch,
		`${BASE_API_URL}/managed-documents/?container=${params.id}`
	).catch(() => []);

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

	const refsRes = await fetch(`${BASE_API_URL}/document-containers/${params.id}/references/`);
	const refs = refsRes.ok ? await refsRes.json() : { references: [], referenced_by: [] };

	return { container, docs, selected, content, revision, refs };
};
