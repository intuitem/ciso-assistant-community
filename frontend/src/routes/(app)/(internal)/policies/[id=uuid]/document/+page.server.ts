import { BASE_API_URL } from '$lib/utils/constants';
import { loadValidationFlowFormData } from '$lib/utils/load';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const { fetch, params, cookies, locals } = event;

	// Load the policy — this is required, fail if unavailable
	const policyRes = await fetch(`${BASE_API_URL}/policies/${params.id}/`);
	if (!policyRes.ok) {
		error(policyRes.status, 'Failed to load policy');
	}
	const policy = await policyRes.json();

	// Determine user's preferred locale
	const userLocale = cookies.get('LOCALE') || 'en';

	// Fetch all documents for this policy (for locale switcher)
	// Gracefully degrade if doc_management is unavailable
	let allDocuments: any[] = [];
	try {
		const allDocsRes = await fetch(`${BASE_API_URL}/managed-documents/?policy=${params.id}`);
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

	// Load validation flow data when feature flag is ON
	let validationFlowForm = null;
	let validationFlowModel = null;
	let activeValidationFlows: any[] = [];

	if (locals.featureflags?.validation_flows) {
		const vfData = await loadValidationFlowFormData({
			event,
			folderId: policy.folder?.id || policy.folder,
			targetField: 'policies',
			targetIds: [params.id]
		});
		validationFlowForm = vfData.validationFlowForm;
		validationFlowModel = vfData.validationFlowModel;

		// Fetch active (submitted) flows for this policy
		try {
			const flowsRes = await fetch(
				`${BASE_API_URL}/validation-flows/?policies=${params.id}&status=submitted`
			);
			if (flowsRes.ok) {
				const flowsData = await flowsRes.json();
				activeValidationFlows = flowsData.results || [];
			}
		} catch {
			// Silently ignore — validation flows are optional
		}
	}

	return {
		policy,
		document,
		revisions,
		currentRevision,
		templates,
		availableLocales,
		userLocale,
		validationFlowForm,
		validationFlowModel,
		activeValidationFlows
	};
};
