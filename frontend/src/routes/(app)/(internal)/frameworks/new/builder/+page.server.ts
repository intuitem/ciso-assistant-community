import { BASE_API_URL } from '$lib/utils/constants';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const foldersRes = await fetch(`${BASE_API_URL}/folders/?content_type=GL`);
	const folders = await foldersRes.json();
	const rootFolder = (folders.results ?? folders)[0];

	if (!rootFolder) {
		throw redirect(302, '/frameworks');
	}

	const res = await fetch(`${BASE_API_URL}/frameworks/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			name: 'Untitled Framework',
			description: '',
			annotation: '',
			folder: rootFolder.id,
			min_score: 0,
			max_score: 100,
			reference_controls: []
		})
	});

	if (!res.ok) {
		throw redirect(302, '/frameworks');
	}

	const framework = await res.json();
	throw redirect(302, `/frameworks/${framework.id}/builder/`);
}) satisfies PageServerLoad;
