import { BASE_API_URL, URN_REGEX } from '$lib/utils/constants';

import { LibraryUploadSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';
import { z } from 'zod';
import { zod } from 'sveltekit-superforms/adapters';
import { tableSourceMapper } from '@skeletonlabs/skeleton';
import { listViewFields } from '$lib/utils/table';
import type { Library } from '$lib/utils/types';
import * as m from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load = (async ({ fetch }) => {
	const stored_libraries_endpoint = `${BASE_API_URL}/stored-libraries/`;
	const loaded_libaries_endpoint = `${BASE_API_URL}/loaded-libraries/`;

	const [stored_libraries_res, loaded_libaries_res] = await Promise.all([
		fetch(stored_libraries_endpoint),
		fetch(loaded_libaries_endpoint)
	]);

	const storedLibraries = await stored_libraries_res.json().then((res) => res.results);
	const loadedLibraries = await loaded_libaries_res.json().then((res) => res.results);

	const prepareRow = (row: Record<string, any>) => {
		row.overview = [
			`Packager: ${row.packager}`,
			`Version: ${row.version}`,
			...Object.entries(row.objects_meta).map(([key, value]) => `${key}: ${value}`)
		];
		row.allowDeleteLibrary = row.allowDeleteLibrary =
			row.reference_count && row.reference_count > 0 ? false : true;
	};

	storedLibraries.forEach(prepareRow);
	loadedLibraries.forEach(prepareRow);

	type libraryURLModel = 'stored-libraries' | 'loaded-libraries';

	const makeHeadData = (URLModel: libraryURLModel) => {
		return listViewFields[URLModel].body.reduce((obj, key, index) => {
			obj[key] = listViewFields[URLModel].head[index];
			return obj;
		}, {});
	};

	const makeBodyData = (libraries: Library[], URLModel: libraryURLModel) =>
		tableSourceMapper(libraries, listViewFields[URLModel].body);

	const makeLibrariesTable = (libraries: Library[], URLModel: libraryURLModel) => {
		return {
			head: makeHeadData(URLModel),
			body: makeBodyData(libraries, URLModel),
			meta: { urlmodel: URLModel, ...libraries }
		};
	};

	const storedLibrariesTable = {
		head: makeHeadData('stored-libraries'),
		meta: { urlmodel: 'stored-libraries', ...storedLibraries },
		body: tableSourceMapper(storedLibraries, listViewFields['stored-libraries'].body)
	};

	const loadedLibrariesTable = makeLibrariesTable(loadedLibraries, 'loaded-libraries');

	const schema = z.object({ id: z.string() });
	const deleteForm = await superValidate(zod(schema));

	return { storedLibrariesTable, loadedLibrariesTable, deleteForm };
}) satisfies PageServerLoad;

// ----------------------------------------------------------- //

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
