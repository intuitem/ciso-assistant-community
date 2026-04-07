import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const frameworksRes = await fetch(`${BASE_API_URL}/frameworks/`);
	const frameworksData = await frameworksRes.json();
	const allFrameworks = frameworksData.results || frameworksData;

	const frameworks = allFrameworks;
	const drafts = allFrameworks.filter((f: any) => f.has_editing_draft);

	return { frameworks, drafts };
}) satisfies PageServerLoad;
