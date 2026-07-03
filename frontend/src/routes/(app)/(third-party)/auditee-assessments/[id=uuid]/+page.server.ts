import { handleErrorResponse, nestedWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { modelSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { error, fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { message, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { ModelInfo } from '$lib/utils/types';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	// params.id is the assignment ID
	const assignmentId = params.id;

	// Fetch the assignment
	const assignmentRes = await fetch(`${BASE_API_URL}/requirement-assignments/${assignmentId}/`);
	if (!assignmentRes.ok) {
		throw error(assignmentRes.status, assignmentRes.statusText);
	}
	const assignmentResult = await assignmentRes.json();
	const assignment = {
		id: assignmentResult.id,
		status: assignmentResult.status,
		events: assignmentResult.events ?? [],
		actor: assignmentResult.actor ?? []
	};

	// Derive the compliance assessment from the assignment
	const caId = assignmentResult.compliance_assessment.id;
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${caId}/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		throw error(res.status, await res.text());
	}
	const compliance_assessment = await res.json();

	const tableModeRes = await fetch(
		`${BASE_API_URL}/requirement-assignments/${assignmentId}/requirements_list/`
	);
	if (!tableModeRes.ok) {
		throw error(tableModeRes.status, tableModeRes.statusText);
	}
	const tableMode = await tableModeRes.json();

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
		requirement_assessments,
		requirements,
		measureModel,
		evidenceModel,
		assignment,
		viewerRole: tableMode.viewer_role ?? 'respondent',
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
		if (result.form) return { form: result.form, newEvidence: result.form.message.object };
		else return result;
	},
	createAppliedControl: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	update: async (event) => {
		const schema = modelSchema('requirement-assessments');
		const id = event.url.searchParams.get('id');
		if (!id) return fail(400, { form: await superValidate(event.request, zod(schema)) });

		const form = await superValidate(event.request, zod(schema));
		if (!form.valid) return fail(400, { form });

		const formData: Record<string, any> = { ...form.data };
		for (const key of ['status', 'result', 'extended_result', 'respondent_alignment']) {
			if (formData[key] === '' || formData[key] === null) delete formData[key];
		}

		const endpoint = `${BASE_API_URL}/requirement-assessments/${id}/`;
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
		return message(form, { object });
	},
	submitAssignment: async (event) => {
		const endpoint = `${BASE_API_URL}/requirement-assignments/${event.params.id}/set_status/`;
		const res = await event.fetch(endpoint, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ status: 'submitted' })
		});
		let body;
		try {
			body = await res.json();
		} catch {
			body = { error: res.statusText };
		}
		return { submitStatus: res.status, submitBody: body };
	}
};
