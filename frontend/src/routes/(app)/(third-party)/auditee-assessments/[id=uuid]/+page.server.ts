import { nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { error, type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { ModelInfo } from '$lib/utils/types';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params, url }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const assignmentId = url.searchParams.get('assignment');

	const res = await fetch(endpoint);
	if (!res.ok) {
		throw error(res.status, await res.text());
	}
	const compliance_assessment = await res.json();

	const assignmentParam = assignmentId ? `?assignment=${assignmentId}` : '';
	const [tableMode, scores] = await Promise.all(
		[`${endpoint}requirements_list/${assignmentParam}`, `${endpoint}global_score/`].map(
			(endpoint) => fetch(endpoint).then((res) => res.json())
		)
	);

	const frameworkEndpoint = `${BASE_API_URL}/frameworks/${compliance_assessment.framework.id}/`;
	const framework = await fetch(frameworkEndpoint).then((res) => res.json());
	compliance_assessment.framework = framework;

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
				evidences: requirementAssessment.evidences.map((evidence) => evidence.id),
				applied_controls: requirementAssessment.applied_controls.map((ac) => ac.id)
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

	// Fetch the user's assignment(s) for this compliance assessment
	const assignmentFilter = assignmentId
		? `id=${assignmentId}`
		: `compliance_assessment=${params.id}`;
	const assignmentsRes = await fetch(
		`${BASE_API_URL}/requirement-assignments/?${assignmentFilter}`
	);
	const assignmentsData = await assignmentsRes.json();
	const assignments =
		assignmentsData.results?.map(
			(a: { id: string; status: string; reviewer_observation: string | null }) => ({
				id: a.id,
				status: a.status,
				reviewer_observation: a.reviewer_observation
			})
		) ?? [];

	return {
		URLModel,
		compliance_assessment,
		scores,
		requirement_assessments,
		requirements,
		measureModel,
		evidenceModel,
		assignments,
		title: compliance_assessment.name
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
		return { status: res.status, body: await res.json() };
	},
	createEvidence: async (event) => {
		const result = await nestedWriteFormAction({ event, action: 'create' });
		return { form: result.form, newEvidence: result.form.message.object };
	},
	createAppliedControl: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	update: async (event) => {
		return nestedWriteFormAction({ event, action: 'edit' });
	},
	submitAssignment: async (event) => {
		const formData = await event.request.formData();
		const id = formData.get('id') as string;

		const endpoint = `${BASE_API_URL}/requirement-assignments/${id}/submit/`;
		const res = await event.fetch(endpoint, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({})
		});
		const body = await res.json();
		return { submitStatus: res.status, submitBody: body };
	}
};
