import { BASE_API_URL } from '$lib/utils/constants';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const { fetch, params, cookies, locals } = event;

	if (!locals.featureflags?.document_management) {
		redirect(302, `/documents`);
	}

	// Load the container — this is required, fail if unavailable
	const containerRes = await fetch(`${BASE_API_URL}/document-containers/${params.id}/`);
	if (!containerRes.ok) {
		error(containerRes.status, 'Failed to load document container');
	}
	const container = await containerRes.json();

	// Determine user's preferred locale
	const userLocale = cookies.get('LOCALE') || 'en';

	// Fetch all documents for this container (for locale switcher)
	// Gracefully degrade if doc_management is unavailable
	let allDocuments: any[] = [];
	try {
		const allDocsRes = await fetch(`${BASE_API_URL}/managed-documents/?container=${params.id}`);
		if (allDocsRes.ok) {
			const allDocsData = await allDocsRes.json();
			allDocuments = allDocsData.results || [];
		}
	} catch {
		// doc_management app may not be available
	}

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
		try {
			const revRes = await fetch(
				`${BASE_API_URL}/document-revisions/?document=${document.id}&ordering=-version_number`
			);
			if (revRes.ok) {
				const revData = await revRes.json();
				revisions = revData.results || [];
			}
		} catch {
			// Gracefully degrade
		}

		// Load current draft or current_revision content
		const draft = revisions.find((r: any) => r.status === 'draft');
		try {
			if (draft) {
				const fullRes = await fetch(`${BASE_API_URL}/document-revisions/${draft.id}/`);
				if (fullRes.ok) {
					currentRevision = await fullRes.json();
				}
			} else if (document.current_revision?.id) {
				const fullRes = await fetch(
					`${BASE_API_URL}/document-revisions/${document.current_revision.id}/`
				);
				if (fullRes.ok) {
					currentRevision = await fullRes.json();
				}
			} else if (revisions.length > 0) {
				const fullRes = await fetch(`${BASE_API_URL}/document-revisions/${revisions[0].id}/`);
				if (fullRes.ok) {
					currentRevision = await fullRes.json();
				}
			}
		} catch {
			// Gracefully degrade
		}
	}

	// Load available templates
	let templates: any[] = [];
	try {
		const templatesRes = await fetch(`${BASE_API_URL}/managed-documents/templates/`);
		if (templatesRes.ok) {
			templates = await templatesRes.json();
		}
	} catch {
		// Templates are optional
	}

	return {
		container,
		document,
		revisions,
		currentRevision,
		templates,
		availableLocales,
		userLocale
	};
};
