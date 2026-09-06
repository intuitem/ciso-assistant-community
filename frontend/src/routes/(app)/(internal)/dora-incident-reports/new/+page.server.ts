import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const URL_MODEL = 'dora-incident-reports';
const ENDPOINT = 'resilience/dora-incident-reports';

async function fetchChoices(fetch: typeof globalThis.fetch, endpoint: string) {
	const res = await fetch(endpoint);
	if (!res.ok) return [];
	const data = await res.json();
	return Object.entries(data).map(([key, value]) => ({
		label: value as string,
		value: key
	}));
}

export const load: PageServerLoad = async ({ url, fetch, locals }) => {
	if (!locals.featureflags?.dora) redirect(302, '/');
	const schema = modelSchema(URL_MODEL);
	const model = getModelInfo(URL_MODEL);

	const incidentId = url.searchParams.get('incident');
	const fromReportId = url.searchParams.get('from');
	let prefillData: Record<string, any> = {
		incident_submission: 'initial_notification'
	};
	let incidentRef: { id: string; name: string } | null = null;

	// Submission type progression: initial → intermediate (multiple allowed) → final
	const SUBMISSION_PROGRESSION = [
		'initial_notification',
		'intermediate_report',
		'final_report',
		'major_incident_reclassified_as_non-major'
	];

	function getNextSubmissionType(currentType: string, existingTypes: string[]): string {
		const currentIndex = SUBMISSION_PROGRESSION.indexOf(currentType);
		// Try advancing to the next type
		for (let i = currentIndex + 1; i < SUBMISSION_PROGRESSION.length; i++) {
			const candidate = SUBMISSION_PROGRESSION[i];
			// intermediate_report allows multiples, others are unique
			if (candidate === 'intermediate_report' || !existingTypes.includes(candidate)) {
				return candidate;
			}
		}
		// Default: intermediate_report (always allowed)
		return 'intermediate_report';
	}

	if (fromReportId) {
		// ── Continue from previous report: copy all data, advance submission type ──
		try {
			const prev = await fetch(`${BASE_API_URL}/${ENDPOINT}/${fromReportId}/object/`).then((r) =>
				r.json()
			);

			// Fetch existing report types for this incident
			let existingTypes: string[] = [];
			if (prev.incident) {
				try {
					const reports = await fetchAllPages(
						fetch,
						`${BASE_API_URL}/${ENDPOINT}/?incident=${prev.incident}`
					);
					existingTypes = reports.map((r: any) => r.incident_submission);
				} catch {
					// Continue without existing types
				}
			}

			// Copy all fields from previous report
			const { id: _id, created_at: _ca, updated_at: _ua, is_submitted: _is, ...prevData } = prev;

			prefillData = {
				...prevData,
				incident_submission: getNextSubmissionType(prev.incident_submission, existingTypes)
			};

			// Resolve incident name for the back link
			if (prev.incident) {
				try {
					const inc = await fetch(`${BASE_API_URL}/incidents/${prev.incident}/`).then((r) =>
						r.json()
					);
					incidentRef = { id: prev.incident, name: inc.name || inc.str || prev.incident };
				} catch {
					incidentRef = { id: prev.incident, name: prev.incident };
				}
			}
		} catch {
			// If previous report fetch fails, fall through to incident-based prefill
		}
	}

	if (!fromReportId || !prefillData.incident) {
		// ── New report from incident: prefill from main entity + incident data ──

		// Fetch main entity (the reporting organization)
		try {
			const mainEntity = await fetch(`${BASE_API_URL}/${ENDPOINT}/main_entity/`).then((r) =>
				r.json()
			);

			if (mainEntity.id) {
				prefillData.submitting_entity = mainEntity.id;
				if (mainEntity.currency) {
					prefillData.report_currency = mainEntity.currency;
				}
				if (mainEntity.dora_competent_authority) {
					prefillData.competent_authority_code = mainEntity.dora_competent_authority;
				}
				const legalIds = mainEntity.legal_identifiers || {};
				const lei = legalIds.LEI || legalIds.EUID || '';
				if (lei) {
					prefillData.financial_entity_code = lei;
				}
			}
		} catch {
			// Main entity fetch is optional
		}

		if (incidentId) {
			try {
				const incident = await fetch(`${BASE_API_URL}/incidents/${incidentId}/`).then((r) =>
					r.json()
				);

				prefillData.incident = incidentId;
				prefillData.folder = incident.folder?.id ?? incident.folder;
				prefillData.incident_description = incident.description || '';
				prefillData.detection_date_time = incident.reported_at || '';
				incidentRef = { id: incidentId, name: incident.name || incident.str || incidentId };

				// Incident's linked entities are the affected entities
				const entityIds: string[] = (incident.entities || []).map((e: any) => e.id ?? e);
				if (entityIds.length > 0) {
					prefillData.affected_entities = entityIds;
				}
			} catch {
				// If incident fetch fails, proceed with what we have
			}
		}
	}

	const form = await superValidate(prefillData, zod(schema), { errors: false });

	// Load all select options in parallel
	const base = `${BASE_API_URL}/${ENDPOINT}`;
	const [
		submissionChoices,
		currencyChoices,
		discoveryChoices,
		classificationCriterionChoices,
		incidentClassificationChoices,
		threatTechniquesChoices,
		rootCauseHlChoices,
		rootCauseDetailedChoices,
		rootCauseAdditionalChoices,
		reportingAuthorityChoices,
		downtimeInfoChoices
	] = await Promise.all([
		fetchChoices(fetch, `${base}/incident_submission/`),
		fetchChoices(fetch, `${base}/report_currency/`),
		fetchChoices(fetch, `${base}/incident_discovery/`),
		fetchChoices(fetch, `${base}/classification_criterion/`),
		fetchChoices(fetch, `${base}/incident_classification/`),
		fetchChoices(fetch, `${base}/threat_techniques/`),
		fetchChoices(fetch, `${base}/root_cause_hl/`),
		fetchChoices(fetch, `${base}/root_cause_detailed/`),
		fetchChoices(fetch, `${base}/root_cause_additional/`),
		fetchChoices(fetch, `${base}/reporting_authority/`),
		fetchChoices(fetch, `${base}/info_duration_service_downtime_actual_or_estimate/`)
	]);

	return {
		form,
		model,
		mode: 'create' as const,
		formAction: '?/create',
		incidentRef,
		selectOptions: {
			incident_submission: submissionChoices,
			report_currency: currencyChoices,
			incident_discovery: discoveryChoices
		},
		allChoices: {
			classificationCriterion: classificationCriterionChoices,
			incidentClassification: incidentClassificationChoices,
			threatTechniques: threatTechniquesChoices,
			rootCauseHl: rootCauseHlChoices,
			rootCauseDetailed: rootCauseDetailedChoices,
			rootCauseAdditional: rootCauseAdditionalChoices,
			reportingAuthority: reportingAuthorityChoices,
			downtimeInfo: downtimeInfoChoices
		}
	};
};

export const actions: Actions = {
	create: async (event) => {
		if (!event.locals.featureflags?.dora) redirect(302, '/');
		return defaultWriteFormAction({
			event,
			urlModel: URL_MODEL,
			action: 'create',
			redirectToWrittenObject: true
		});
	}
};
