import { BASE_API_URL } from '#lib/utils/constants.js';
import type { PageServerLoad } from './$types';

// Audits an audit guide applies to: on its own framework, or on one with the
// same requirement numbering (a licensed copy, a translation).
export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/compliance-assessments/auditor_preread_audits/`);
	const audits = res.ok ? await res.json() : [];
	return { audits, title: 'Auditor pre-read' };
};
