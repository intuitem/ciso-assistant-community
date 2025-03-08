import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions } from '@sveltejs/kit';
import { fail } from 'assert';
import { setFlash } from 'sveltekit-flash-message/server';
import * as m from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/folders/get_accessible_folders_and_perimeters/`;
	const res = await fetch(endpoint);
	const data = await res.json();
	return { data: data, title: 'Data import wizard' };
}) satisfies PageServerLoad;

export const actions: Actions = {
	default: async (event) => {
		const { request, fetch } = event;
		const formData = await request.formData();

		// Extract the file and other form values
		const file = formData.get('file') as File;
		const model = formData.get('model') as string;
		const folder = formData.get('folder') as string;
		const perimeter = formData.get('perimeter') as string;

		if (!file?.name || file?.name === 'undefined') {
			return fail(400, {
				error: true,
				message: 'You must provide a file to upload'
			});
		}

		const endpoint = `${BASE_API_URL}/data-wizard/load-file/`;
		const response = await fetch(endpoint, {
			method: 'POST',
			headers: {
				'Content-Disposition': `attachment; filename="${file.name}"`,
				'Content-Type': file.type,
				'X-Model-Type': model,
				'X-Folder-Id': folder,
				'X-Perimeter-Id': perimeter
			},
			body: file
		});

		const data = await response.json();

		if (response.status >= 400) {
			console.error(data);
			switch (data.error) {
				case 'errorBackupInvalidVersion':
					setFlash({ type: 'error', message: m.backupVersionError() }, event);
					break;
				case 'GreaterBackupVersion':
					setFlash({ type: 'error', message: m.backupGreaterVersionError() }, event);
					break;
				case 'LowerBackupVersion':
					setFlash({ type: 'error', message: m.backupLowerVersionError() }, event);
					break;
				default:
					setFlash({ type: 'error', message: m.backupLoadingError() }, event);
					break;
			}
		}

		return {
			status: response.status,
			body: JSON.stringify(data)
		};
	}
};
