import { BASE_API_URL } from '$lib/utils/constants';

import { nestedDeleteFormAction } from '$lib/utils/actions';
import { safeTranslate } from '$lib/utils/i18n';
import { LibraryUploadSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import { m } from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const storedLibrariesEndpoint = `${BASE_API_URL}/stored-libraries/`;
	const loadedLibrariesEndpoint = `${BASE_API_URL}/loaded-libraries/`;
	const updatableLibrariesEndpoint = `${loadedLibrariesEndpoint}available-updates/`;

	const [storedLibrariesResponse, loadedLibrariesResponse, updatableLibrariesResponse] =
		await Promise.all([
			fetch(storedLibrariesEndpoint),
			fetch(loadedLibrariesEndpoint),
			fetch(updatableLibrariesEndpoint)
		]);

	const storedLibraries = await storedLibrariesResponse.json();
	const loadedLibraries = await loadedLibrariesResponse.json();
	const updatableLibraries = await updatableLibrariesResponse.json();

	const prepareRow = (row: Record<string, any>) => {
		row.overview = [
			`Packager: ${row.packager}`,
			`Version: ${row.version}`,
			...Object.entries(row.objects_meta).map(([key, value]) => `${key}: ${value}`)
		];
		row.allowDeleteLibrary = row.allowDeleteLibrary =
			row.reference_count && row.reference_count > 0 ? false : true;
	};

	storedLibraries.results.forEach(prepareRow);
	loadedLibraries.results.forEach(prepareRow);

	type libraryURLModel = 'stored-libraries' | 'loaded-libraries';

	const makeHeadData = (URLModel: libraryURLModel) => {
		return listViewFields[URLModel].body.reduce((obj, key, index) => {
			obj[key] = listViewFields[URLModel].head[index];
			return obj;
		}, {});
	};

	const storedLibrariesTable = {
		head: makeHeadData('stored-libraries'),
		meta: { urlmodel: 'stored-libraries', ...storedLibraries },
		body: tableSourceMapper(storedLibraries.results, listViewFields['stored-libraries'].body)
	};

	const loadedLibrariesTable = {
		head: makeHeadData('loaded-libraries'),
		meta: { urlmodel: 'loaded-libraries', ...loadedLibraries },
		body: tableSourceMapper(loadedLibraries.results, listViewFields['loaded-libraries'].body)
	};

	const schema = z.object({ id: z.string() });
	const deleteForm = await superValidate(zod(schema));

	return {
		storedLibrariesTable,
		loadedLibrariesTable,
		updatableLibraries,
		deleteForm,
		title: m.libraries()
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	upload: async (event) => {
		const formData = await event.request.formData();
		const form = await superValidate(formData, zod(LibraryUploadSchema));

		if (formData.has('file')) {
			const { file } = Object.fromEntries(formData) as { file: File };
			// Should i check if attachment.size > 0 ?
			const endpoint = `${BASE_API_URL}/stored-libraries/upload/`;
			const req = await event.fetch(endpoint, {
				method: 'POST',
				headers: {
					'Content-Disposition': `attachment; filename=${file.name}`
				},
				body: file
			});
			if (!req.ok) {
				const response = await req.json();
				console.error(response);

				const translate_error = safeTranslate(response.error);
				const toast_error_message =
					translate_error ?? m.libraryLoadingError() + '(' + response.error + ')';

				setFlash({ type: 'error', message: toast_error_message }, event);
				delete form.data['file']; // This removes a warning: Cannot stringify arbitrary non-POJOs (data..form.data.file)
				return fail(400, { form });
			}
			setFlash({ type: 'success', message: m.librarySuccessfullyLoaded() }, event);
		} else {
			setFlash({ type: 'error', message: m.noLibraryDetected() }, event);
			return fail(400, { form });
		}
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
