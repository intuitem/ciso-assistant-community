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
		const formData = Object.fromEntries(await request.formData());
		if (!(formData.file as File)?.name || (formData.file as File)?.name === 'undefined') {
			return fail(400, {
				error: true,
				message: 'You must provide a file to upload'
			});
		}

		const { file } = formData as { file: File };

		const endpoint = `${BASE_API_URL}/data-wizard/load-file/`;
		const response = await fetch(endpoint, {
			method: 'POST',
			headers: {
				'Content-Disposition': `attachment; filename="${file.name}"`,
				'Content-Type': file.type
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
