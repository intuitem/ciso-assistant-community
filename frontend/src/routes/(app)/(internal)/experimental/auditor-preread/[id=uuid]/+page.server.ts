import { BASE_API_URL } from '#lib/utils/constants.js';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	// ?guide=<framework urn> applies a guide the numbering only partly matches.
	const guide = url.searchParams.get('guide');
	const query = guide ? `?guide=${encodeURIComponent(guide)}` : '';
	const [auditRes, prereadRes] = await Promise.all([
		fetch(`${BASE_API_URL}/compliance-assessments/${params.id}/`),
		fetch(`${BASE_API_URL}/compliance-assessments/${params.id}/auditor_preread/${query}`)
	]);
	if (!auditRes.ok || !prereadRes.ok) error(auditRes.ok ? prereadRes.status : auditRes.status);
	const audit = await auditRes.json();
	return { audit, preread: await prereadRes.json(), title: `Auditor pre-read: ${audit.name}` };
};
