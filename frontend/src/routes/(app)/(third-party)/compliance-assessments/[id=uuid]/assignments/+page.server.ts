import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { z } from 'zod';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

// Schema for the assignment form
const assignmentSchema = z.object({
	actor: z.string().uuid().optional()
});

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const compliance_assessment = await res.json();

	const tree = await fetch(`${endpoint}tree/`).then((res) => res.json());

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
			actor: { id: string; str: string; type?: string };
			requirement_assessments: { id: string }[];
		}) => ({
			id: assignment.id,
			actor: {
				id: assignment.actor.id,
				str: assignment.actor.str,
				type: assignment.actor.type || 'user'
			},
			requirement_assessments: assignment.requirement_assessments.map((ra) => ra.id)
		})
	);

	return {
		URLModel,
		compliance_assessment,
		tree,
		assignmentForm,
		assignments,
		title: `${compliance_assessment.name} - Assignments`
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();
		const actor = formData.get('actor') as string;
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
		const actor = formData.get('actor') as string;
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
	}
};
