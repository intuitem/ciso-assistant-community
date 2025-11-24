import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions, PageServerLoad } from './$types';
import { fail } from '@sveltejs/kit';

export const load = (async ({ fetch }) => {
	// Load folders for assets and entities
	const foldersEndpoint = `${BASE_API_URL}/folders/`;
	const foldersRes = await fetch(foldersEndpoint);
	const foldersData = await foldersRes.json();
	const folders = foldersData.results || foldersData;

	// Load EBIOS RM studies for feared events
	const studiesEndpoint = `${BASE_API_URL}/ebios-rm/studies/`;
	const studiesRes = await fetch(studiesEndpoint);
	const studiesData = await studiesRes.json();
	const studies = studiesData.results || studiesData;

	return { folders, studies };
}) satisfies PageServerLoad;

export const actions: Actions = {
	default: async ({ request, fetch }) => {
		const formData = await request.formData();
		const type = formData.get('type') as string;
		const itemsText = formData.get('items_text') as string;
		const folderId = formData.get('folder') as string;
		const studyId = formData.get('study') as string;

		// Validate based on type
		if (!itemsText || !itemsText.trim()) {
			return fail(400, {
				success: false,
				error: `Please enter at least one ${type}`
			});
		}

		let endpoint = '';
		let bodyKey = '';
		let containerKey = '';
		let containerId = '';
		let itemTypePlural = '';
		let itemTypeSingular = '';

		if (type === 'assets') {
			if (!folderId) {
				return fail(400, { success: false, error: 'Please select a folder' });
			}
			endpoint = `${BASE_API_URL}/assets/batch-create/`;
			bodyKey = 'assets_text';
			containerKey = 'folder';
			containerId = folderId;
			itemTypePlural = 'assets';
			itemTypeSingular = 'asset';
		} else if (type === 'entities') {
			if (!folderId) {
				return fail(400, { success: false, error: 'Please select a folder' });
			}
			endpoint = `${BASE_API_URL}/entities/batch-create/`;
			bodyKey = 'entities_text';
			containerKey = 'folder';
			containerId = folderId;
			itemTypePlural = 'entities';
			itemTypeSingular = 'entity';
		} else if (type === 'feared-events') {
			if (!studyId) {
				return fail(400, { success: false, error: 'Please select an EBIOS RM study' });
			}
			endpoint = `${BASE_API_URL}/ebios-rm/feared-events/batch-create/`;
			bodyKey = 'feared_events_text';
			containerKey = 'ebios_rm_study';
			containerId = studyId;
			itemTypePlural = 'feared_events';
			itemTypeSingular = 'feared event';
		} else {
			return fail(400, { success: false, error: 'Invalid type' });
		}

		try {
			const response = await fetch(endpoint, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					[bodyKey]: itemsText,
					[containerKey]: containerId
				})
			});

			const data = await response.json();

			if (!response.ok) {
				return fail(response.status, {
					success: false,
					error: data.error || `Failed to create ${itemTypePlural}`,
					type,
					...data
				});
			}

			return {
				success: true,
				type,
				created: data.created,
				skipped: data.skipped || data.reused || 0,
				items: data[itemTypePlural] || data.assets,
				skipped_items: data[`skipped_${itemTypePlural}`] || data.reused_assets || [],
				errors: data.errors
			};
		} catch (error) {
			console.error(`Error creating ${itemTypePlural}:`, error);
			return fail(500, {
				success: false,
				type,
				error: `An error occurred while creating ${itemTypePlural}`
			});
		}
	}
};
