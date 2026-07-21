import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error, fail, type Actions, type NumericRange } from '@sveltejs/kit';

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}`;
	const assessmentRes = await event.fetch(`${endpoint}/`);
	if (!assessmentRes.ok)
		error(assessmentRes.status as NumericRange<400, 599>, await assessmentRes.json());
	const assessment = await assessmentRes.json();
	const asset =
		event.url.searchParams.get('asset') ??
		(assessment.assets?.length === 1 ? assessment.assets[0].id : null);
	const treeRes = await event.fetch(
		`${endpoint}/tree/${asset ? `?asset=${encodeURIComponent(asset)}` : ''}`
	);
	if (!treeRes.ok) error(treeRes.status as NumericRange<400, 599>, await treeRes.json());
	const tree = await treeRes.json();
	return {
		assessment,
		tree: tree.tree,
		assets: tree.assets,
		selectedAsset: asset,
		title: assessment.name
	};
};

export const actions: Actions = {
	setResult: async (event) => {
		const formData = await event.request.formData();
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/upload-results/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					asset: formData.get('asset'),
					source: 'manual',
					...(formData.get('run_id') ? { run_id: formData.get('run_id') } : {}),
					results: [{ ref_id: formData.get('ref_id'), result: formData.get('result') }]
				})
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return await res.json();
	}
};
