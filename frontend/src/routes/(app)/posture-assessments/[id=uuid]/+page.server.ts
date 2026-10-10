import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}`;
	const fetchJson = (url: string) => event.fetch(url).then((res) => (res.ok ? res.json() : null));
	const [detailData, posture, actionPlan, trend, runs] = await Promise.all([
		loadDetail({
			event,
			model: getModelInfo('posture-assessments'),
			id: event.params.id
		}),
		fetchJson(`${endpoint}/posture/`),
		fetchJson(`${endpoint}/action-plan/`),
		fetchJson(`${endpoint}/trend/`),
		fetchJson(`${endpoint}/runs/`)
	]);

	return { ...detailData, posture, actionPlan, trend, runs };
};

// atomic M2M add/remove server-side — avoids the read-then-PATCH race on assets
async function mutateAssets(event: any, action: 'add_m2m' | 'remove_m2m', assetId: string) {
	const res = await event.fetch(`${BASE_API_URL}/automation/posture-assessments/batch-action/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			action,
			ids: [event.params.id],
			field: 'assets',
			value: [assetId]
		})
	});
	if (!res.ok) return fail(res.status, await res.json());
	const body = await res.json();
	if (body.failed?.length)
		return fail(400, { error: body.failed[0]?.error ?? 'batch action failed' });
	return null;
}

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	addAsset: async (event) => {
		const formData = await event.request.formData();
		const assetId = formData.get('asset');
		if (!assetId) return fail(400, { error: 'asset required' });
		const result = await mutateAssets(event, 'add_m2m', assetId as string);
		return result ?? { added: assetId };
	},
	removeAsset: async (event) => {
		const formData = await event.request.formData();
		const assetId = formData.get('asset');
		if (!assetId) return fail(400, { error: 'asset required' });
		const result = await mutateAssets(event, 'remove_m2m', assetId as string);
		return result ?? { removed: assetId };
	},
	importFile: async (event) => {
		const formData = await event.request.formData();
		const file = formData.get('file');
		const asset = formData.get('asset');
		const assets = formData.get('assets');
		const mapping = formData.get('mapping');
		if (!file || (!asset && !assets && !mapping))
			return fail(400, { error: 'asset and file are required' });
		const fd = new FormData();
		if (asset) fd.set('asset', asset);
		if (assets) fd.set('assets', assets);
		if (mapping) fd.set('mapping', mapping);
		fd.set('file', file);
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/import-results/`,
			{ method: 'POST', body: fd }
		);
		if (!res.ok) return fail(res.status, await res.json());
		return { importSummary: await res.json() };
	},
	analyzeImport: async (event) => {
		const formData = await event.request.formData();
		const file = formData.get('file');
		if (!file) return fail(400, { error: 'file is required' });
		const fd = new FormData();
		fd.set('file', file);
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/analyze-import/`,
			{ method: 'POST', body: fd }
		);
		if (!res.ok) return fail(res.status, await res.json());
		return { analysis: await res.json() };
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
