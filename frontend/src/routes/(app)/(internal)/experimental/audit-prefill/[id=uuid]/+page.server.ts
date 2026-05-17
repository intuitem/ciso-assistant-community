import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

async function fetchJson(fetch: typeof globalThis.fetch, url: string) {
	const res = await fetch(url);
	if (!res.ok) return null;
	return res.json();
}

export const load = (async ({ fetch, params }) => {
	const runRes = await fetch(`${BASE_API_URL}/chat/agent-runs/${params.id}/`);
	if (!runRes.ok) {
		throw error(runRes.status, 'Agent run not found.');
	}
	const run = await runRes.json();

	// The target is a ComplianceAssessment — fetch it for header context.
	let complianceAssessment: any = null;
	if (run.target_object_id) {
		complianceAssessment = await fetchJson(
			fetch,
			`${BASE_API_URL}/compliance-assessments/${run.target_object_id}/`
		);
	}

	const actionsData = await fetchJson(
		fetch,
		`${BASE_API_URL}/chat/agent-actions/?agent_run=${params.id}&ordering=created_at`
	);
	const actions = actionsData?.results ?? actionsData ?? [];

	// Wave 2 needs requirement-assessment metadata to render verdicts in
	// context (ref_id, requirement text, section). Pull them only when this
	// is a Wave-2 run, to keep Wave-1 pages snappy.
	let requirementAssessments: any[] = [];
	let appliedControls: any[] = [];
	if (run.config?.wave === 2 && complianceAssessment?.id) {
		const [rasData, acsData] = await Promise.all([
			fetchJson(
				fetch,
				`${BASE_API_URL}/requirement-assessments/?compliance_assessment=${complianceAssessment.id}`
			),
			fetchJson(fetch, `${BASE_API_URL}/applied-controls/?folder=${run.folder?.id ?? ''}`)
		]);
		requirementAssessments = rasData?.results ?? rasData ?? [];
		appliedControls = acsData?.results ?? acsData ?? [];
	}

	return { run, complianceAssessment, actions, requirementAssessments, appliedControls };
}) satisfies PageServerLoad;
