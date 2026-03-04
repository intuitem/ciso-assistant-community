import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json();
	const { preset_id, folder_name, folder_id } = body;

	const response = await fetch(`${BASE_API_URL}/stored-libraries/${preset_id}/apply/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ folder_name, folder_id })
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ error: 'Failed to apply preset' }));
		return json(error, { status: response.status });
	}

	const result = await response.json();
	return json(result, { status: 201 });
};
