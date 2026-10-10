import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const studyPath = `/ebios-rm/${event.params.id}/workshop-1/ebios-rm-study`;
	const next = `${studyPath}?activity=one`;
	redirect(302, `${studyPath}/edit?activity=one&next=${encodeURIComponent(next)}`);
};
