import { BASE_API_URL, URN_REGEX } from '$lib/utils/constants';

import { LibraryUploadSchema } from '$lib/utils/schemas';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';
import { z } from 'zod';
import { tableSourceMapper } from '@skeletonlabs/skeleton';
import { listViewFields } from '$lib/utils/table';
import type { Library, urlModel } from '$lib/utils/types';
import * as m from '$paraglide/messages';
import { localItems } from '$lib/utils/locales';
import { languageTag } from '$paraglide/runtime';
import { zod } from 'sveltekit-superforms/adapters';

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/libraries/`;

	const res = await fetch(endpoint);
	const libraries: Library[] = await res.json().then((res) => res.results);

	function countObjects(library: Library) {
		const result: { [key: string]: any } = new Object();
		for (const [key, value] of Object.entries(library.objects)) {
			if (Array.isArray(value)) {
				const str = key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ');
				result[str] = value.length;
			} else {
				for (const [key2, value2] of Object.entries(value)) {
					if (key2 === 'requirements') {
						const str = key2.charAt(0).toUpperCase() + key2.slice(1);
						result[str] = value2.length;
					}
				}
			}
		}
		return result;
	}

	libraries.forEach((row) => {
		row.overview = [
			`Provider: ${row.provider}`,
			`Packager: ${row.packager}`,
			...Object.entries(countObjects(row)).map(([key, value]) => `${key}: ${value}`)
		];
		row.allowDeleteLibrary = row.reference_count && row.reference_count > 0 ? false : true;
	});

	const headData: Record<string, string> = listViewFields['libraries' as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields['libraries' as urlModel].head[index];
			return obj;
		},
		{}
	);

	const bodyData = (libraries) =>
		tableSourceMapper(libraries, listViewFields['libraries' as urlModel].body);

	const librariesTable: TableSource = (libraries: Library[]) => {
		return {
			head: headData,
			body: bodyData(libraries),
			meta: libraries
		};
	};

	const defaultLibrariesTable = librariesTable(
		libraries.filter((lib) => !lib.id)
	);

	const importedLibrariesTable = librariesTable(libraries.filter((lib) => lib.id));

	const schema = z.object({ id: z.string() });
	const deleteForm = await superValidate(zod(schema));

	return { libraries, defaultLibrariesTable, importedLibrariesTable, deleteForm };
}) satisfies PageServerLoad;

export const actions: Actions = {
	upload: async (event) => {
		const formData = await event.request.formData();
		const form = await superValidate(formData, zod(LibraryUploadSchema));

		if (formData.has('file')) {
			const { file } = Object.fromEntries(formData) as { file: File };

			if (file.size <= 0) {
				return fail(400, { form });
			}

			const endpoint = `${BASE_API_URL}/libraries/upload/`;
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

				const translate_error = localItems(languageTag())[response.error];
				const toast_error_message = translate_error ?? m.libraryImportError();

				setFlash({ type: 'error', message: toast_error_message }, event);
				return fail(400, { form });
			}
			setFlash({ type: 'success', message: m.librarySuccessfullyImported() }, event);
		} else {
			setFlash({ type: 'error', message: m.noLibraryDetected() }, event);
			return fail(400, { form });
		}
	},
	delete: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ id: z.string().regex(URN_REGEX) });
		const deleteForm = await superValidate(formData, zod(schema));

		const id = deleteForm.data.id;
		const endpoint = `${BASE_API_URL}/libraries/${id}/`;

		if (!deleteForm.valid) {
			console.error(deleteForm.errors);
			return fail(400, { form: deleteForm });
		}

		if (formData.has('delete')) {
			const requestInitOptions: RequestInit = {
				method: 'DELETE'
			};
			const res = await event.fetch(endpoint, requestInitOptions);
			if (!res.ok) {
				const response = await res.json();
				console.error(response);
				setFlash({ type: 'error', message: `${response}` }, event);
				if (response.non_field_errors) {
					setError(deleteForm, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form: deleteForm });
			}
			setFlash(
				{ type: 'success', message: m.successfullyDeletedObject({ object: 'library' }) },
				event
			);
		}
		return { deleteForm };
	}
};
