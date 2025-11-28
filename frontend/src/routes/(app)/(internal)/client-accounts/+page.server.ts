import { BASE_API_URL } from '$lib/utils/constants';
import { redirect, type Actions, fail } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

// Schema for creating a new account
const createAccountSchema = z.object({
	name: z.string().min(1, 'Company name is required'),
	slug: z.string().optional(),
	email: z.string().email('Invalid email address'),
	phone: z.string().optional(),
	address: z.string().optional(),
	status: z.enum(['active', 'suspended', 'expired', 'trial']).default('trial'),
	plan: z.enum(['free', 'basic', 'pro', 'enterprise']).default('free'),
	subscription_start: z.string().optional(),
	subscription_end: z.string().min(1, 'Subscription end date is required'),
	max_users: z.number().min(1).default(5),
	max_domains: z.number().min(1).default(1),
	notes: z.string().optional(),
	admin_email: z.string().email().optional(),
	admin_first_name: z.string().optional(),
	admin_last_name: z.string().optional()
});

// Schema for delete action
const deleteSchema = z.object({
	id: z.string().uuid()
});

export const load: PageServerLoad = async ({ fetch, url, locals }) => {
	// Check if user is superuser
	const userResponse = await fetch(`${BASE_API_URL}/iam/current-user/`);
	const user = await userResponse.json();

	if (!user.is_admin) {
		redirect(302, '/');
	}

	// Fetch accounts with filters
	const status = url.searchParams.get('status') || '';
	const plan = url.searchParams.get('plan') || '';
	const search = url.searchParams.get('search') || '';
	const expiringSoon = url.searchParams.get('expiring_soon') || '';

	let apiUrl = `${BASE_API_URL}/accounts/client-accounts/`;
	const params = new URLSearchParams();
	if (status) params.append('status', status);
	if (plan) params.append('plan', plan);
	if (search) params.append('search', search);
	if (expiringSoon) params.append('expiring_soon', expiringSoon);

	if (params.toString()) {
		apiUrl += `?${params.toString()}`;
	}

	const accountsResponse = await fetch(apiUrl);
	const accounts = await accountsResponse.json();

	// Fetch stats
	const statsResponse = await fetch(`${BASE_API_URL}/accounts/client-accounts/stats/`);
	const stats = await statsResponse.json();

	// Create forms
	const createForm = await superValidate(zod(createAccountSchema));
	const deleteForm = await superValidate(zod(deleteSchema));

	return {
		accounts: accounts.results || accounts,
		stats,
		createForm,
		deleteForm,
		title: 'Client Accounts',
		user
	};
};

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();
		const form = await superValidate(formData, zod(createAccountSchema));

		if (!form.valid) {
			return fail(400, { form });
		}

		const data = {
			...form.data,
			max_users: Number(form.data.max_users) || 5,
			max_domains: Number(form.data.max_domains) || 1
		};

		const response = await event.fetch(`${BASE_API_URL}/accounts/client-accounts/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(data)
		});

		if (!response.ok) {
			const error = await response.json();
			setFlash({ type: 'error', message: error.detail || 'Failed to create account' }, event);
			return fail(response.status, { form });
		}

		setFlash({ type: 'success', message: 'Account created successfully' }, event);
		return { form };
	},

	delete: async (event) => {
		const formData = await event.request.formData();
		const form = await superValidate(formData, zod(deleteSchema));

		if (!form.valid) {
			return fail(400, { form });
		}

		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${form.data.id}/`,
			{
				method: 'DELETE'
			}
		);

		if (!response.ok) {
			setFlash({ type: 'error', message: 'Failed to delete account' }, event);
			return fail(response.status, { form });
		}

		setFlash({ type: 'success', message: 'Account deleted successfully' }, event);
		return { form };
	},

	activate: async (event) => {
		const formData = await event.request.formData();
		const id = formData.get('id');

		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${id}/activate/`,
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
		const formData = await event.request.formData();
		const id = formData.get('id');

		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${id}/suspend/`,
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
		const id = formData.get('id');
		const days = formData.get('days');

		const response = await event.fetch(
			`${BASE_API_URL}/accounts/client-accounts/${id}/extend_subscription/`,
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
