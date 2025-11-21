import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions, PageServerLoad } from './$types';
import { fail } from '@sveltejs/kit';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/folders/`;
	const res = await fetch(endpoint);
	const data = await res.json();
	const folders = data.results || data;
	return { folders };
}) satisfies PageServerLoad;

export const actions: Actions = {
	default: async ({ request, fetch }) => {
		const formData = await request.formData();
		const assetsText = formData.get('assets_text') as string;
		const folderId = formData.get('folder') as string;

		if (!assetsText || !assetsText.trim()) {
			return fail(400, {
				success: false,
				error: 'Please enter at least one asset'
			});
		}

		if (!folderId) {
			return fail(400, {
				success: false,
				error: 'Please select a folder'
			});
		}

		const endpoint = `${BASE_API_URL}/assets/batch-create/`;

		try {
			const response = await fetch(endpoint, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					assets_text: assetsText,
					folder: folderId
				})
			});

			const data = await response.json();

			if (!response.ok) {
				return fail(response.status, {
					success: false,
					error: data.error || 'Failed to create assets',
					...data
				});
			}

			return {
				success: true,
				created: data.created,
				assets: data.assets,
				errors: data.errors
			};
		} catch (error) {
			console.error('Error creating assets:', error);
			return fail(500, {
				success: false,
				error: 'An error occurred while creating assets'
			});
		}
	}
};
