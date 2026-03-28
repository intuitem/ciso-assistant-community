import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/** Create a new framework and return its id/name as JSON */
export const POST: RequestHandler = async ({ fetch }) => {
	// Fetch root folder
	const foldersRes = await fetch(`${BASE_API_URL}/folders/?content_type=GL`);
	const folders = await foldersRes.json();
	const rootFolder = (folders.results ?? folders)[0];

	if (!rootFolder) {
		error(400, { message: 'No root folder found' });
	}

	// Create framework
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
		const data = await res.json();
		error(res.status as NumericRange<400, 599>, data);
	}

	const framework = await res.json();
	return json({ id: framework.id, name: framework.name });
};
