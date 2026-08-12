import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const runsRes = await fetch(`${BASE_API_URL}/chat/questionnaire-runs/?ordering=-created_at`);
	const runsData = await runsRes.json();
	return {
		runs: runsData.results ?? runsData
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	upload: async ({ request, fetch }) => {
		const incoming = await request.formData();
		const file = incoming.get('file');
		const folder = incoming.get('folder');
		const title = (incoming.get('title') as string | null) ?? '';

		if (!(file instanceof File) || !file.name) {
			return fail(400, { error: 'Please select an Excel file.' });
		}
		if (!folder) {
			return fail(400, { error: 'Please select a domain.' });
		}

		const forwarded = new FormData();
		forwarded.append('file', file, file.name);
		forwarded.append('folder', folder as string);
		if (title) forwarded.append('title', title);

		const response = await fetch(`${BASE_API_URL}/chat/questionnaire-runs/upload/`, {
			method: 'POST',
			body: forwarded
		});

		const data = await response.json().catch(() => ({}));
		if (!response.ok) {
			return fail(response.status, {
				error: data.detail || 'Upload failed.'
			});
		}

		throw redirect(303, `/experimental/questionnaire-autopilot/${data.id}`);
	}
};
