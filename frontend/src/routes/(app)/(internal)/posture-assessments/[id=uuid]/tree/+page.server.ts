import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}`;
	const asset = event.url.searchParams.get('asset');
	const [assessment, tree] = await Promise.all([
		event.fetch(`${endpoint}/`).then((res) => res.json()),
		event
			.fetch(`${endpoint}/tree/${asset ? `?asset=${encodeURIComponent(asset)}` : ''}`)
			.then((res) => res.json())
	]);
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
					results: [{ ref_id: formData.get('ref_id'), result: formData.get('result') }]
				})
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return { ok: true };
	}
};
