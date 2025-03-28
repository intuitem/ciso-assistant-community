import { nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import type { Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { ModelInfo } from '$lib/utils/types';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const [compliance_assessment, tableMode] = await Promise.all(
		[endpoint, `${endpoint}requirements_list/`].map((endpoint) =>
			fetch(endpoint).then((res) => res.json())
		)
	);

	const evidenceModel = getModelInfo('evidences');
	const evidenceCreateSchema = modelSchema('evidences');
	const scoreSchema = z.object({
		is_scored: z.boolean().optional(),
		score: z.number().optional().nullable(),
		documentation_score: z.number().optional().nullable()
	});
	const requirement_assessments = await Promise.all(
		tableMode.requirement_assessments.map(async (requirementAssessment) => {
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
				evidences: requirementAssessment.evidences.map((evidence) => evidence.id)
			};
			const updateForm = await superValidate(object, zod(updateSchema), { errors: false });
			return {
				...requirementAssessment,
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
		requirement_assessments,
		requirements,
		evidenceModel,
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
		return { status: res.status, body: await res.json() };
	},
	createEvidence: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	update: async (event) => {
		return nestedWriteFormAction({ event, action: 'edit' });
	}
};
