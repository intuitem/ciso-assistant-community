import { base } from '$app/paths';
import type { PageServerLoad, Actions } from './$types';
import { error, fail } from '@sveltejs/kit';
import { getModelInfo } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { superValidate } from 'sveltekit-superforms/server';
import { zod } from 'sveltekit-superforms/adapters';
import { dataAssetSchema } from '$lib/utils/schemas';

const MODEL = 'data-assets';

export const load: PageServerLoad = async ({ params, fetch, depends }) => {
	depends(`app:data-asset:${params.id}`);

	const model = getModelInfo(MODEL);

	if (!model) {
		throw error(404, 'Model not found');
	}

	try {
		const response = await fetch(`${base}/api/privacy/data-assets/${params.id}/`);
		if (!response.ok) {
			if (response.status === 404) {
				throw error(404, 'Data asset not found');
			}
			throw error(response.status, 'Failed to load data asset');
		}

		const dataAsset = await response.json();

		// Load related consent records
		const consentResponse = await fetch(`${base}/api/privacy/consent-records/?data_subject_id=${encodeURIComponent(dataAsset.asset_id)}`);
		const consentRecords = consentResponse.ok ? (await consentResponse.json()).results || [] : [];

		// Load related data subject rights
		const rightsResponse = await fetch(`${base}/api/privacy/data-subject-rights/?data_subject_id=${encodeURIComponent(dataAsset.asset_id)}`);
		const dataSubjectRights = rightsResponse.ok ? (await rightsResponse.json()).results || [] : [];

		return {
			title: `${safeTranslate('Data Asset')}: ${dataAsset.asset_name}`,
			dataAsset,
			consentRecords,
			dataSubjectRights,
			model,
			form: await superValidate(dataAsset, zod(dataAssetSchema))
		};
	} catch (err) {
		console.error('Error loading data asset:', err);
		throw error(500, 'Failed to load data asset');
	}
};

export const actions: Actions = {
	update: async ({ request, params, fetch }) => {
		const form = await superValidate(request, zod(dataAssetSchema));

		if (!form.valid) {
			return fail(400, { form });
		}

		try {
			const response = await fetch(`${base}/api/privacy/data-assets/${params.id}/`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(form.data)
			});

			if (!response.ok) {
				return fail(response.status, {
					form,
					error: 'Failed to update data asset'
				});
			}

			const updatedDataAsset = await response.json();

			return {
				form: await superValidate(updatedDataAsset, zod(dataAssetSchema)),
				success: true
			};
		} catch (err) {
			console.error('Error updating data asset:', err);
			return fail(500, {
				form,
				error: 'Internal server error'
			});
		}
	},

	conduct_pia: async ({ params, fetch }) => {
		try {
			const response = await fetch(`${base}/api/privacy/data-assets/${params.id}/conduct-pia/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					findings: 'PIA conducted through web interface',
					assessor_user_id: 'current-user-id', // This would come from session
					assessor_username: 'Current User'
				})
			});

			if (!response.ok) {
				return fail(response.status, {
					error: 'Failed to conduct PIA'
				});
			}

			return { success: true, pia_completed: true };
		} catch (err) {
			console.error('Error conducting PIA:', err);
			return fail(500, {
				error: 'Internal server error'
			});
		}
	},

	delete: async ({ params, fetch }) => {
		try {
			const response = await fetch(`${base}/api/privacy/data-assets/${params.id}/`, {
				method: 'DELETE'
			});

			if (!response.ok) {
				return fail(response.status, {
					error: 'Failed to delete data asset'
				});
			}

			return { success: true, deleted: true };
		} catch (err) {
			console.error('Error deleting data asset:', err);
			return fail(500, {
				error: 'Internal server error'
			});
		}
	}
};
