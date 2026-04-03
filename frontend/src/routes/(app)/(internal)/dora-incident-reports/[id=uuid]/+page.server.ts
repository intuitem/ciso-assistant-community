import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import type { Actions } from '@sveltejs/kit';
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

export const load: PageServerLoad = async ({ params, fetch }) => {
	const schema = modelSchema(URL_MODEL);
	const model = getModelInfo(URL_MODEL);

	// Fetch existing object
	const objectEndpoint = `${BASE_API_URL}/${ENDPOINT}/${params.id}/object/`;
	const object = await fetch(objectEndpoint).then((res) => res.json());
	const form = await superValidate(object, zod(schema), { errors: false });

	// Resolve incident name for the back link
	let incidentRef: { id: string; name: string } | null = null;
	if (object.incident) {
		try {
			const inc = await fetch(`${BASE_API_URL}/incidents/${object.incident}/`).then(
				(r) => r.json()
			);
			incidentRef = { id: object.incident, name: inc.name || inc.str || object.incident };
		} catch {
			incidentRef = { id: object.incident, name: object.incident };
		}
	}

	// Fetch validation status
	let validation = { valid: false, errors: [] as string[] };
	try {
		const res = await fetch(
			`${BASE_API_URL}/${ENDPOINT}/${params.id}/validate_report/`
		);
		if (res.ok) {
			validation = await res.json();
		}
	} catch {
		// Validation is optional
	}

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

	// Fetch users for contact fill helper
	let userOptions: { id: string; label: string; email: string }[] = [];
	try {
		const usersRes = await fetch(`${BASE_API_URL}/users/`);
		if (usersRes.ok) {
			const usersData = await usersRes.json();
			const results = usersData.results ?? usersData ?? [];
			userOptions = results.map((u: any) => ({
				id: u.id,
				label: `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.email,
				email: u.email || ''
			}));
		}
	} catch {
		// Optional
	}

	return {
		form,
		model,
		object,
		incidentRef,
		validation,
		userOptions,
		reportId: params.id,
		mode: 'edit' as const,
		formAction: '?/update',
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
	update: async (event) => {
		return defaultWriteFormAction({
			event,
			urlModel: URL_MODEL,
			action: 'edit'
		});
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
