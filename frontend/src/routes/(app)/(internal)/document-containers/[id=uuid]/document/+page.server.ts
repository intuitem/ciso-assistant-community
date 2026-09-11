import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { pickWorkingRevision } from '$lib/utils/documentRevisions';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const { fetch, params, cookies, locals, url } = event;

	if (!locals.featureflags?.document_management) {
		redirect(302, `/documents`);
	}

	// Load the container — this is required, fail if unavailable
	const containerRes = await fetch(`${BASE_API_URL}/document-containers/${params.id}/`);
	if (!containerRes.ok) {
		error(containerRes.status, 'Failed to load document container');
	}
	const container = await containerRes.json();

	// Determine target locale: explicit ?locale= wins over the user's cookie
	const userLocale = url.searchParams.get('locale') || cookies.get('LOCALE') || 'en';

	// Fetch all documents for this container (for locale switcher)
	// Gracefully degrade if doc_management is unavailable
	let allDocuments: any[] = [];
	try {
		allDocuments = await fetchAllPages(
			fetch,
			`${BASE_API_URL}/managed-documents/?container=${params.id}`
		);
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
			revisions = await fetchAllPages(
				fetch,
				`${BASE_API_URL}/document-revisions/?document=${document.id}&ordering=-version_number`
			);
		} catch {
			// Gracefully degrade
		}

		const working = pickWorkingRevision(revisions, document.current_revision?.id);
		try {
			if (working) {
				const fullRes = await fetch(`${BASE_API_URL}/document-revisions/${working.id}/`);
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
		const templatesRes = await fetch(
			`${BASE_API_URL}/managed-documents/templates/?document_type=${container.document_type}`
		);
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
