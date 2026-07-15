import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';

function flattenChecks(nodes: any[], acc: any[] = []) {
	for (const node of nodes) {
		if (node.assessable && node.ref_id) acc.push(node);
		if (node.children?.length) flattenChecks(node.children, acc);
	}
	return acc;
}

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}`;
	const [assessment, tree, posture] = await Promise.all([
		event.fetch(`${endpoint}/`).then((res) => res.json()),
		event.fetch(`${endpoint}/tree/`).then((res) => res.json()),
		event.fetch(`${endpoint}/posture/`).then((res) => res.json())
	]);
	return {
		assessment,
		checks: flattenChecks(tree.tree),
		assets: tree.assets,
		posture,
		title: assessment.name
	};
};

export const actions: Actions = {
	setCell: async (event) => {
		const formData = await event.request.formData();
		const body: Record<string, any> = {
			asset: formData.get('asset'),
			source: 'manual',
			results: [{ ref_id: formData.get('ref_id'), result: formData.get('result') }]
		};
		const runId = formData.get('run_id');
		if (runId) body.run_id = runId;
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/upload-results/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return await res.json();
	}
};
