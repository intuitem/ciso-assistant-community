import { BASE_API_URL } from '$lib/utils/constants';
import { redirect, type Actions, fail, error } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

// Schema for editing account
const editAccountSchema = z.object({
	name: z.string().min(1, 'Company name is required'),
	email: z.string().email('Invalid email address'),
	phone: z.string().optional().nullable(),
	address: z.string().optional().nullable(),
	status: z.enum(['active', 'suspended', 'expired', 'trial']),
	plan: z.enum(['free', 'basic', 'pro', 'enterprise']),
	subscription_end: z.string().min(1, 'Subscription end date is required'),
	max_users: z.number().min(1),
	max_domains: z.number().min(1),
	notes: z.string().optional().nullable()
});

export const load: PageServerLoad = async ({ params, fetch }) => {
	// Check if user is superuser
	const userResponse = await fetch(`${BASE_API_URL}/iam/current-user/`);
	const user = await userResponse.json();

	if (!user.is_admin) {
		redirect(302, '/');
	}

	// Fetch account details
	const accountResponse = await fetch(`${BASE_API_URL}/accounts/client-accounts/${params.id}/`);

	if (!accountResponse.ok) {
		error(404, 'Account not found');
	}

	const account = await accountResponse.json();

	// Fetch users for this account
	const usersResponse = await fetch(
		`${BASE_API_URL}/accounts/client-accounts/${params.id}/users/`
	);
	const usersData = await usersResponse.json();

	// Create edit form with account data
	const editForm = await superValidate(
		{
			name: account.name,
			email: account.email,
			phone: account.phone || '',
			address: account.address || '',
			status: account.status,
			plan: account.plan,
			subscription_end: account.subscription_end,
			max_users: account.max_users,
			max_domains: account.max_domains,
			notes: account.notes || ''
		},
		zod(editAccountSchema)
	);

	return {
		account,
		users: usersData.users || [],
		editForm,
		title: account.name,
		user
	};
};

export const actions: Actions = {
	update: async (event) => {
		const formData = await event.request.formData();
		const form = await superValidate(formData, zod(editAccountSchema));

		if (!form.valid) {
			return fail(400, { form });
		}

		const data = {
			...form.data,
			max_users: Number(form.data.max_users),
			max_domains: Number(form.data.max_domains)
		};

		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${event.params.id}/`,
			{
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(data)
			}
		);

		if (!response.ok) {
			const error = await response.json();
			setFlash({ type: 'error', message: error.detail || 'Failed to update account' }, event);
			return fail(response.status, { form });
		}

		setFlash({ type: 'success', message: 'Account updated successfully' }, event);
		return { form };
	},

	activate: async (event) => {
		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${event.params.id}/activate/`,
			{
				method: 'POST'
			}
		);

		if (!response.ok) {
			setFlash({ type: 'error', message: 'Failed to activate account' }, event);
			return fail(response.status);
		}

		setFlash({ type: 'success', message: 'Account activated successfully' }, event);
		return { success: true };
	},

	suspend: async (event) => {
		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${event.params.id}/suspend/`,
			{
				method: 'POST'
			}
		);

		if (!response.ok) {
			setFlash({ type: 'error', message: 'Failed to suspend account' }, event);
			return fail(response.status);
		}

		setFlash({ type: 'success', message: 'Account suspended successfully' }, event);
		return { success: true };
	},

	extend: async (event) => {
		const formData = await event.request.formData();
		const days = formData.get('days');

		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${event.params.id}/extend_subscription/`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ days: Number(days) })
			}
		);

		if (!response.ok) {
			setFlash({ type: 'error', message: 'Failed to extend subscription' }, event);
			return fail(response.status);
		}

		setFlash({ type: 'success', message: `Subscription extended by ${days} days` }, event);
		return { success: true };
	}
};
