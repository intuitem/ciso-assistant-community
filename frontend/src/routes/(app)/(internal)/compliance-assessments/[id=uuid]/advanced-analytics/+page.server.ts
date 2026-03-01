import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}`;

	// Block on the compliance assessment itself (needed for header/context)
	const compliance_assessment = await fetch(`${endpoint}/`).then((res) => res.json());

	// Stream all analytics data as unresolved promises
	const sectionCompliancePromise = fetch(`${endpoint}/section_compliance/`)
		.then((res) => res.json())
		.catch(() => ({ sections: [] }));

	const controlsCoveragePromise = fetch(`${endpoint}/controls_coverage/`)
		.then((res) => res.json())
		.catch(() => ({
			total_assessable: 0,
			with_controls: 0,
			without_controls: 0,
			coverage_percent: 0,
			control_status_distribution: {},
			requirements_by_control_count: {}
		}));

	const complianceTimelinePromise = fetch(`${endpoint}/compliance_timeline/`)
		.then((res) => res.json())
		.catch(() => ({ timeline: [], comparable_audits: [] }));

	const igBreakdownPromise = fetch(`${endpoint}/implementation_groups_breakdown/`)
		.then((res) => res.json())
		.catch(() => ({ groups: [] }));

	const mappingProjectionPromise = fetch(`${endpoint}/frameworks/`)
		.then((res) => res.json())
		.catch(() => []);

	const evidenceCoveragePromise = fetch(`${endpoint}/evidence_coverage/`)
		.then((res) => res.json())
		.catch(() => ({
			total_assessable: 0,
			with_evidence: 0,
			without_evidence: 0,
			coverage_percent: 0,
			direct_only: 0,
			indirect_only: 0,
			both: 0,
			evidence_status_distribution: {}
		}));

	const threatsPromise = fetch(`${endpoint}/threats_metrics/`)
		.then((res) => res.json())
		.catch(() => ({ threats: [], total_unique_threats: 0, graph: { nodes: [] } }));

	const exceptionsPromise = fetch(`${endpoint}/exceptions_summary/`)
		.then((res) => res.json())
		.catch(() => ({
			total: 0,
			status_distribution: {},
			severity_distribution: {},
			exceptions: []
		}));

	return {
		URLModel,
		compliance_assessment,
		title: 'Advanced Analytics',
		stream: {
			sectionCompliance: sectionCompliancePromise,
			controlsCoverage: controlsCoveragePromise,
			complianceTimeline: complianceTimelinePromise,
			igBreakdown: igBreakdownPromise,
			mappingProjection: mappingProjectionPromise,
			evidenceCoverage: evidenceCoveragePromise,
			threats: threatsPromise,
			exceptions: exceptionsPromise
		}
	};
}) satisfies PageServerLoad;
