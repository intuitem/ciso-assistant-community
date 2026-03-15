import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	// Load the policy
	const policyRes = await fetch(`${BASE_API_URL}/policies/${params.id}/`);
	const policy = await policyRes.json();

	// Try to find existing document for this policy
	const docRes = await fetch(`${BASE_API_URL}/policy-documents/?policy=${params.id}`);
	const docData = await docRes.json();

	let document = docData.results?.[0] || null;
	let revisions: any[] = [];
	let currentRevision: any = null;

	if (document) {
		// Load revisions
		const revRes = await fetch(
			`${BASE_API_URL}/policy-document-revisions/?document=${document.id}&ordering=-version_number`
		);
		const revData = await revRes.json();
		revisions = revData.results || [];

		// Load current draft or current_revision content
		const draft = revisions.find((r: any) => r.status === 'draft' || r.status === 'Draft');
		if (draft) {
			const fullRes = await fetch(`${BASE_API_URL}/policy-document-revisions/${draft.id}/`);
			currentRevision = await fullRes.json();
		} else if (document.current_revision?.id) {
			const fullRes = await fetch(
				`${BASE_API_URL}/policy-document-revisions/${document.current_revision.id}/`
			);
			currentRevision = await fullRes.json();
		} else if (revisions.length > 0) {
			const fullRes = await fetch(`${BASE_API_URL}/policy-document-revisions/${revisions[0].id}/`);
			currentRevision = await fullRes.json();
		}
	}

	// Load available templates
	const templatesRes = await fetch(`${BASE_API_URL}/policy-documents/templates/`);
	const templates = await templatesRes.json();

	return {
		policy,
		document,
		revisions,
		currentRevision,
		templates
	};
};
