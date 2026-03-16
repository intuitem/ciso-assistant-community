import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, cookies }) => {
	// Load the policy
	const policyRes = await fetch(`${BASE_API_URL}/policies/${params.id}/`);
	const policy = await policyRes.json();

	// Determine user's preferred locale
	const userLocale = cookies.get('LOCALE') || 'en';

	// Fetch all documents for this policy (for locale switcher)
	const allDocsRes = await fetch(`${BASE_API_URL}/managed-documents/?policy=${params.id}`);
	const allDocsData = await allDocsRes.json();
	const allDocuments = allDocsData.results || [];

	// Extract available locales from existing documents
	const availableLocales: string[] = allDocuments.map((d: any) => d.locale || 'en');

	// Try to find the document matching user's locale
	let document =
		allDocuments.find((d: any) => d.locale === userLocale) ||
		allDocuments.find((d: any) => d.default_locale) ||
		allDocuments[0] ||
		null;

	let revisions: any[] = [];
	let currentRevision: any = null;

	if (document) {
		// Load revisions
		const revRes = await fetch(
			`${BASE_API_URL}/document-revisions/?document=${document.id}&ordering=-version_number`
		);
		const revData = await revRes.json();
		revisions = revData.results || [];

		// Load current draft or current_revision content
		const draft = revisions.find((r: any) => r.status === 'draft' || r.status === 'Draft');
		if (draft) {
			const fullRes = await fetch(`${BASE_API_URL}/document-revisions/${draft.id}/`);
			currentRevision = await fullRes.json();
		} else if (document.current_revision?.id) {
			const fullRes = await fetch(
				`${BASE_API_URL}/document-revisions/${document.current_revision.id}/`
			);
			currentRevision = await fullRes.json();
		} else if (revisions.length > 0) {
			const fullRes = await fetch(`${BASE_API_URL}/document-revisions/${revisions[0].id}/`);
			currentRevision = await fullRes.json();
		}
	}

	// Load available templates
	const templatesRes = await fetch(`${BASE_API_URL}/managed-documents/templates/`);
	const templates = await templatesRes.json();

	return {
		policy,
		document,
		revisions,
		currentRevision,
		templates,
		availableLocales,
		userLocale
	};
};
