import { handleErrorResponse, nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { ModelInfo } from '$lib/utils/types';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const [compliance_assessment, tableMode, scores] = await Promise.all(
		[endpoint, `${endpoint}requirements_list/`, `${endpoint}global_score/`].map((endpoint) =>
			fetch(endpoint).then((res) => res.json())
		)
	);

	const frameworkId = compliance_assessment.framework?.id;
	if (frameworkId) {
		const frameworkEndpoint = `${BASE_API_URL}/frameworks/${frameworkId}/`;
		const framework = await fetch(frameworkEndpoint).then((res) => res.json());
		compliance_assessment.framework = framework;
	}

	const measureModel = getModelInfo('applied-controls');
	const measureCreateSchema = modelSchema('applied-controls');

	const evidenceModel = getModelInfo('evidences');
	const evidenceCreateSchema = modelSchema('evidences');
	const scoreSchema = z.object({
		is_scored: z.boolean().optional(),
		score: z.number().optional().nullable(),
		documentation_score: z.number().optional().nullable()
	});
	const requirement_assessments = await Promise.all(
		tableMode.requirement_assessments.map(async (requirementAssessment) => {
			// TODO: merge initial data ?
			const measureInitialData = {
				requirement_assessments: [requirementAssessment.id],
				folder: requirementAssessment.folder.id
			};
			const measureCreateForm = await superValidate(measureInitialData, zod(measureCreateSchema), {
				errors: false
			});
			const evidenceInitialData = {
				requirement_assessments: [requirementAssessment.id],
				folder: requirementAssessment.folder.id
			};
			const evidenceCreateForm = await superValidate(
				evidenceInitialData,
				zod(evidenceCreateSchema),
				{
					errors: false
				}
			);
			const observationBuffer = requirementAssessment.observation;
			const scoreForm = await superValidate(
				{
					is_scored: requirementAssessment.is_scored,
					score: requirementAssessment.score,
					documentation_score: requirementAssessment.documentation_score
				},
				zod(scoreSchema)
			);
			const updateSchema = modelSchema('requirement-assessments');
			const updatedModel: ModelInfo = getModelInfo('requirement-assessments');
			const object = {
				...requirementAssessment,
				folder: requirementAssessment.folder.id,
				requirement: requirementAssessment.requirement.id,
				compliance_assessment: requirementAssessment.compliance_assessment.id,
				...(requirementAssessment.evidences !== undefined && {
					evidences: requirementAssessment.evidences.map((evidence) => evidence.id)
				}),
				...(requirementAssessment.applied_controls !== undefined && {
					applied_controls: requirementAssessment.applied_controls.map((ac) => ac.id)
				})
			};
			const updateForm = await superValidate(object, zod(updateSchema), { errors: false });
			return {
				...requirementAssessment,
				measureCreateForm,
				evidenceCreateForm,
				observationBuffer,
				scoreForm,
				updateForm,
				updatedModel,
				object
			};
		})
	);

	const requirementAssessmentsById = requirement_assessments.reduce(
		(acc, requirementAssessment) => {
			acc[requirementAssessment.requirement] = requirementAssessment;
			return acc;
		},
		{}
	);

	const requirements = tableMode.requirements.map((requirement) => {
		if (requirementAssessmentsById[requirement.id]) {
			return requirementAssessmentsById[requirement.id];
		}
		return requirement;
	});

	return {
		URLModel,
		compliance_assessment,
		scores,
		requirement_assessments,
		requirements,
		measureModel,
		evidenceModel,
		viewerRole: tableMode.viewer_role ?? 'auditor',
		title: m.tableMode()
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	updateRequirementAssessment: async (event) => {
		const data = await event.request.json();
		const value: { id: string; result: string } = data;
		const URLModel = 'requirement-assessments';
		const endpoint = `${BASE_API_URL}/${URLModel}/${value.id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(value)
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		const body = await res.json();
		return { status: res.status, body };
	},
	createEvidence: async (event) => {
		const result = await nestedWriteFormAction({ event, action: 'create' });
		return { form: result.form, newEvidence: result.form.message.object };
	},
	createAppliedControl: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	update: async (event) => {
		// Custom update for requirement-assessments that strips fields hidden by
		// field_visibility before PATCHing. The generic nestedWriteFormAction
		// would send empty values for fields the viewer never saw, which the
		// backend rejects (e.g. `status: ""` is not a valid enum choice).
		const URLModel = 'requirement-assessments';
		const schema = modelSchema(URLModel);
		const id = event.url.searchParams.get('id');
		if (!id) {
			console.error('Missing id parameter in update action');
			return fail(400, { form: await superValidate(event.request, zod(schema)) });
		}
		const endpoint = `${BASE_API_URL}/${URLModel}/${id}/`;
		const form = await superValidate(event.request, zod(schema));

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form });
		}

		const formData: Record<string, any> = { ...form.data };

		let currentRa: Record<string, any>;
		try {
			const currentRaResponse = await event.fetch(endpoint);
			if (!currentRaResponse.ok) {
				return handleErrorResponse({ event, response: currentRaResponse, form });
			}
			currentRa = await currentRaResponse.json();
		} catch (error) {
			console.error('Failed to fetch requirement assessment before update', error);
			return fail(502, { form });
		}

		const visibilityControlled = [
			'result',
			'extended_result',
			'status',
			'score',
			'is_scored',
			'documentation_score',
			'observation',
			'answers',
			'evidences',
			'applied_controls'
		];
		for (const key of visibilityControlled) {
			if (!(key in currentRa)) {
				delete formData[key];
			}
		}
		// extended_result is a qualifier on result; strip it alongside a hidden result.
		if (!('result' in currentRa)) {
			delete formData.extended_result;
		}

		// The detail GET above does not honor viewer_role and returns the
		// auditor view regardless of caller, so visibility-driven stripping
		// alone misses fields the respondent never saw but that zod defaulted
		// to "". Drop empty enum values to avoid DRF "is not a valid choice"
		// errors on PATCH (e.g. status: "").
		for (const key of ['status', 'result', 'extended_result', 'respondent_alignment']) {
			if (formData[key] === '' || formData[key] === null) {
				delete formData[key];
			}
		}

		const response = await event.fetch(endpoint, {
			method: 'PATCH',
			body: JSON.stringify(formData)
		});

		if (!response.ok) return handleErrorResponse({ event, response, form });

		const object = await response.json();
		setFlash(
			{
				type: 'success',
				message: m.successfullySavedObject({
					object: safeTranslate('requirementAssessment').toLowerCase()
				})
			},
			event
		);
		return { form, object };
	}
};
