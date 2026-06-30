import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions } from '@sveltejs/kit';
import { fail } from '@sveltejs/kit'; // Import from kit instead of assert
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

// Models with an "update existing" target, mapped to their list endpoint.
const TARGET_ENDPOINTS: Record<string, string> = {
	ComplianceAssessment: 'compliance-assessments',
	RiskAssessment: 'risk-assessments',
	FindingsAssessment: 'findings-assessments'
};

export const load = (async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/folders/get_accessible_objects/`;
	const res = await fetch(endpoint);
	const data = await res.json();

	// Accessible assessments per model, for the "update existing" picker.
	const targets: Record<string, { id: string; name: string }[]> = {};
	await Promise.all(
		Object.entries(TARGET_ENDPOINTS).map(async ([model, path]) => {
			try {
				const r = await fetch(`${BASE_API_URL}/${path}/?page_size=1000`);
				if (!r.ok) {
					targets[model] = [];
					return;
				}
				const body = await r.json();
				const rows = Array.isArray(body) ? body : (body.results ?? []);
				targets[model] = rows.map((o: any) => ({ id: o.id, name: o.str ?? o.name }));
			} catch {
				targets[model] = [];
			}
		})
	);
	data.targets = targets;

	return { data: data, title: m.dataWizard() };
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
		const framework = formData.get('framework') as string;
		const matrix = formData.get('matrix') as string;
		const target = formData.get('target') as string;
		const onConflict = (formData.get('onConflict') as string) || 'stop';

		if (!file?.name || file?.name === 'undefined') {
			// Using the fail function from SvelteKit
			return fail(400, {
				success: false,
				error: 'noFileProvided',
				message: 'You must provide a file to upload'
			});
		}

		const endpoint = `${BASE_API_URL}/data-wizard/load-file/`;

		try {
			const response = await fetch(endpoint, {
				method: 'POST',
				headers: {
					'Content-Disposition': `attachment; filename="${file.name}"`,
					'Content-Type': file.type,
					'X-Model-Type': model,
					'X-Folder-Id': folder,
					'X-Perimeter-Id': perimeter,
					'X-Framework-Id': framework,
					'X-Matrix-Id': matrix,
					'X-Target-Id': target,
					'X-On-Conflict': onConflict
				},
				body: file
			});

			const data = await response.json();

			if (response.status >= 400) {
				console.error(data);
				const errorCode = data.error || 'unknown_error';

				switch (errorCode) {
					case 'errorBackupInvalidVersion':
						setFlash({ type: 'error', message: m.backupVersionError() }, event);
						break;
					case 'GreaterBackupVersion':
						setFlash({ type: 'error', message: m.backupGreaterVersionError() }, event);
						break;
					default:
						setFlash({ type: 'error', message: 'error while loading your file' }, event);
						break;
				}

				return {
					success: false,
					status: response.status,
					error: errorCode,
					message: data.message,
					results: data.results
				};
			}

			return {
				success: true,
				status: response.status,
				message: data.message || 'File uploaded successfully',
				results: data.results
			};
		} catch (error) {
			console.error('Error during upload:', error);
			return {
				success: false,
				error: 'connection_error',
				message: 'Could not connect to the server'
			};
		}
	}
};
