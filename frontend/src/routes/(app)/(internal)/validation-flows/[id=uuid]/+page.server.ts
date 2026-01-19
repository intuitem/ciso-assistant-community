import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad, Actions } from './$types';
import { fail } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/validation-flows/${params.id}/`;

	const validation_flow = await fetch(endpoint).then((res) => res.json());

	return {
		validation_flow,
		title: validation_flow.str
	};
};

export const actions: Actions = {
	approve: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const event_notes = formData.get('notes') as string;

		const updateData = {
			status: 'accepted',
			event_notes
		};

		const response = await fetch(`${BASE_API_URL}/validation-flows/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.validationApproved() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},

	reject: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const event_notes = formData.get('notes') as string;

		const updateData = {
			status: 'rejected',
			event_notes
		};

		const response = await fetch(`${BASE_API_URL}/validation-flows/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.validationRejected() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},

	revoke: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const event_notes = formData.get('notes') as string;

		const updateData = {
			status: 'revoked',
			event_notes
		};

		const response = await fetch(`${BASE_API_URL}/validation-flows/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.validationRevoked() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},

	drop: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const event_notes = formData.get('notes') as string;

		const updateData = {
			status: 'dropped',
			event_notes
		};

		const response = await fetch(`${BASE_API_URL}/validation-flows/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.validationDropped() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},

	request_changes: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const event_notes = formData.get('notes') as string;

		const updateData = {
			status: 'change_requested',
			event_notes
		};

		const response = await fetch(`${BASE_API_URL}/validation-flows/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.changesRequested() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},

	resubmit: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const event_notes = formData.get('notes') as string;

		const updateData = {
			status: 'submitted',
			event_notes
		};

		const response = await fetch(`${BASE_API_URL}/validation-flows/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.validationResubmitted() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	}
};
