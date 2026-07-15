import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}`;
	const [detailData, posture, actionPlan, trend, runs] = await Promise.all([
		loadDetail({
			event,
			model: getModelInfo('posture-assessments'),
			id: event.params.id
		}),
		event.fetch(`${endpoint}/posture/`).then((res) => res.json()),
		event.fetch(`${endpoint}/action-plan/`).then((res) => res.json()),
		event.fetch(`${endpoint}/trend/`).then((res) => res.json()),
		event.fetch(`${endpoint}/runs/`).then((res) => res.json())
	]);

	return { ...detailData, posture, actionPlan, trend, runs };
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	addAsset: async (event) => {
		const formData = await event.request.formData();
		const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}/`;
		const assessment = await event.fetch(endpoint).then((res) => res.json());
		const current = (assessment.assets ?? []).map((a: any) => a.id);
		const assetId = formData.get('asset');
		if (!assetId) return fail(400, { error: 'asset required' });
		const res = await event.fetch(endpoint, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ assets: [...current, assetId] })
		});
		if (!res.ok) return fail(res.status, await res.json());
		return { added: assetId };
	},
	removeAsset: async (event) => {
		const formData = await event.request.formData();
		const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}/`;
		const assessment = await event.fetch(endpoint).then((res) => res.json());
		const assetId = formData.get('asset');
		const kept = (assessment.assets ?? [])
			.map((a: any) => a.id)
			.filter((id: string) => id !== assetId);
		const res = await event.fetch(endpoint, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ assets: kept })
		});
		if (!res.ok) return fail(res.status, await res.json());
		return { removed: assetId };
	},
	importFile: async (event) => {
		const formData = await event.request.formData();
		const file = formData.get('file');
		const asset = formData.get('asset');
		if (!file || !asset) return fail(400, { error: 'asset and file are required' });
		const fd = new FormData();
		fd.set('asset', asset);
		fd.set('file', file);
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/import-results/`,
			{ method: 'POST', body: fd }
		);
		if (!res.ok) return fail(res.status, await res.json());
		return { importSummary: await res.json() };
	},
	purgeAsset: async (event) => {
		const formData = await event.request.formData();
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/purge-asset/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ asset: formData.get('asset') })
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return await res.json();
	},
	createFinding: async (event) => {
		const formData = await event.request.formData();
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/create-finding/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					requirement: formData.get('requirement'),
					asset: formData.get('asset')
				})
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return { createdFinding: await res.json() };
	}
};
