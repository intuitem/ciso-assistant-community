import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { z } from 'zod';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';

// Schema for the assignment form
const assignmentSchema = z.object({
	actor: z.array(z.string().uuid()).default([])
});

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const compliance_assessment = await res.json();

	const tree = await fetch(`${endpoint}tree/`).then((res) => res.json());

	// Fetch framework to get implementation groups definition
	const frameworkId = compliance_assessment.framework?.id;
	let implementationGroupsDefinition: Array<{
		ref_id: string;
		name: string;
		description?: string;
	}> = [];
	if (frameworkId) {
		const fwRes = await fetch(`${BASE_API_URL}/frameworks/${frameworkId}/`);
		if (fwRes.ok) {
			const framework = await fwRes.json();
			implementationGroupsDefinition = framework.implementation_groups_definition || [];
		}
	}

	// Create form for assignment
	const assignmentForm = await superValidate(zod(assignmentSchema));

	// Fetch existing assignments from backend
	const assignmentsRes = await fetch(
		`${BASE_API_URL}/requirement-assignments/?compliance_assessment=${params.id}`
	);
	const assignmentsData = await assignmentsRes.json();

	// Transform backend data to frontend format
	const assignments = assignmentsData.results.map(
		(assignment: {
			id: string;
			actor: Array<{ id: string; str: string; type?: string }>;
			requirement_assessments: { id: string }[];
			status: string;
			events: Array<{
				id: string;
				event_type: string;
				event_actor: { id: string; email: string; first_name: string; last_name: string } | null;
				event_notes: string | null;
				created_at: string;
			}>;
		}) => ({
			id: assignment.id,
			actor: assignment.actor.map((a) => ({
				id: a.id,
				str: a.str,
				type: a.type || 'user'
			})),
			requirement_assessments: assignment.requirement_assessments.map((ra) => ra.id),
			status: assignment.status,
			events: assignment.events ?? []
		})
	);

	return {
		URLModel,
		compliance_assessment,
		tree,
		assignmentForm,
		assignments,
		implementationGroupsDefinition,
		title: compliance_assessment.name
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();
		const actor = JSON.parse(formData.get('actor') as string);
		const requirement_assessments = JSON.parse(formData.get('requirement_assessments') as string);
		const compliance_assessment = formData.get('compliance_assessment') as string;
		const folder = formData.get('folder') as string;

		const endpoint = `${BASE_API_URL}/requirement-assignments/`;

		const requestInitOptions: RequestInit = {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				actor,
				requirement_assessments,
				compliance_assessment,
				folder
			})
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		const body = await res.json();
		return { status: res.status, body };
	},
	update: async (event) => {
		const formData = await event.request.formData();
		const id = formData.get('id') as string;
		const actor = JSON.parse(formData.get('actor') as string);
		const requirement_assessments = JSON.parse(formData.get('requirement_assessments') as string);

		const endpoint = `${BASE_API_URL}/requirement-assignments/${id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				actor,
				requirement_assessments
			})
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		const body = await res.json();
		return { status: res.status, body };
	},
	delete: async (event) => {
		const formData = await event.request.formData();
		const id = formData.get('id') as string;

		const endpoint = `${BASE_API_URL}/requirement-assignments/${id}/`;

		const requestInitOptions: RequestInit = {
			method: 'DELETE'
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		return { status: res.status };
	},
	setStatus: async (event) => {
		const formData = await event.request.formData();
		const id = formData.get('id') as string;
		const targetStatus = formData.get('status') as string;
		const reviewer_observation = formData.get('reviewer_observation') as string | null;

		const endpoint = `${BASE_API_URL}/requirement-assignments/${id}/set_status/`;
		const payload: Record<string, string> = { status: targetStatus };
		if (reviewer_observation) {
			payload.reviewer_observation = reviewer_observation;
		}
		const res = await event.fetch(endpoint, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
		const body = await res.json();
		return { status: res.status, body };
	}
};
