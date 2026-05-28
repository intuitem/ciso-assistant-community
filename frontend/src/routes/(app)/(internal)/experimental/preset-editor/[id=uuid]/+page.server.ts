import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const presetRes = await fetch(`${BASE_API_URL}/presets/${params.id}/`);
	if (!presetRes.ok) {
		throw error(presetRes.status, 'Preset not found');
	}
	const preset = await presetRes.json();

	// Use loaded-libraries (not frameworks/risk-matrices) — scaffolds reference
	// the *library* URN, not the framework's own URN. The validator and executor
	// resolve via LoadedLibrary.objects.filter(urn=...), so the editor must
	// store library URNs to keep the data shape compatible with library YAMLs.
	const [frameworks, riskMatrices, frameworkDetails] = await Promise.all([
		fetch(`${BASE_API_URL}/loaded-libraries/?object_type=framework&ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => []),
		fetch(`${BASE_API_URL}/loaded-libraries/?object_type=risk_matrix&ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => []),
		// Frameworks list (separate fetch) — used to resolve implementation_groups_definition
		// for a chosen library URN. Lookup is by library URN.
		fetch(`${BASE_API_URL}/frameworks/?ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => [])
	]);

	return { preset, frameworks, riskMatrices, frameworkDetails };
};
