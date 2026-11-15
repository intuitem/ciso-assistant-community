import { BASE_API_URL } from '#lib/utils/constants.js';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const [auditRes, prereadRes] = await Promise.all([
		fetch(`${BASE_API_URL}/compliance-assessments/${params.id}/`),
		fetch(`${BASE_API_URL}/compliance-assessments/${params.id}/auditor_preread/`)
	]);
	if (!auditRes.ok || !prereadRes.ok) error(auditRes.ok ? prereadRes.status : auditRes.status);
	const audit = await auditRes.json();
	return { audit, preread: await prereadRes.json(), title: `Auditor pre-read: ${audit.name}` };
};
