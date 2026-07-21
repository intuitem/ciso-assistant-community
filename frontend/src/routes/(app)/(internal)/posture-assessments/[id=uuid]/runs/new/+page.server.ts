import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error, fail, redirect, type Actions, type NumericRange } from '@sveltejs/kit';

function flattenChecks(nodes: any[], acc: any[] = []) {
	for (const node of nodes) {
		if (node.assessable && node.ref_id) acc.push(node);
		if (node.children?.length) flattenChecks(node.children, acc);
	}
	return acc;
}

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}`;
	const [assessmentRes, treeRes] = await Promise.all([
		event.fetch(`${endpoint}/`),
		event.fetch(`${endpoint}/tree/`)
	]);
	if (!assessmentRes.ok)
		error(assessmentRes.status as NumericRange<400, 599>, await assessmentRes.json());
	if (!treeRes.ok) error(treeRes.status as NumericRange<400, 599>, await treeRes.json());
	const [assessment, tree] = await Promise.all([assessmentRes.json(), treeRes.json()]);
	const asset =
		event.url.searchParams.get('asset') ??
		(assessment.assets?.length === 1 ? assessment.assets[0].id : null);
	let selectedAssetName = tree.assets.find((a: any) => a.id === asset)?.str ?? null;
	if (asset && !selectedAssetName) {
		const remote = await event.fetch(`${BASE_API_URL}/assets/${asset}/`);
		if (remote.ok) {
			const body = await remote.json();
			selectedAssetName = body.folder?.str ? `${body.folder.str}/${body.name}` : body.name;
		}
	}

	const checks = flattenChecks(tree.tree);
	const from = event.url.searchParams.get('from');
	let prefill: Record<string, string> = {};
	let prefillDropped = 0;
	if (from && asset) {
		const sourceRun = await event.fetch(`${endpoint}/runs/${from}/`);
		if (sourceRun.ok) {
			const body = await sourceRun.json();
			const known = new Set(checks.map((c: any) => c.ref_id));
			for (const row of body.results) {
				if (row.asset.id !== asset) continue;
				if (known.has(row.requirement.ref_id)) {
					prefill[row.requirement.ref_id] = row.result;
				} else {
					prefillDropped += 1;
				}
			}
		}
	}

	return {
		assessment,
		checks,
		assets: tree.assets,
		selectedAsset: asset,
		selectedAssetName,
		prefill,
		prefillDropped,
		title: assessment.name
	};
};

export const actions: Actions = {
	saveRun: async (event) => {
		const formData = await event.request.formData();
		const asset = formData.get('asset');
		const results = [];
		for (const [key, value] of formData.entries()) {
			if (key.startsWith('result:') && value) {
				results.push({ ref_id: key.slice('result:'.length), result: value });
			}
		}
		if (!asset || !results.length) {
			return fail(400, { error: 'asset and at least one result are required' });
		}
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/upload-results/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ asset, source: 'manual', results })
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		redirect(303, `/posture-assessments/${event.params.id}`);
	}
};
