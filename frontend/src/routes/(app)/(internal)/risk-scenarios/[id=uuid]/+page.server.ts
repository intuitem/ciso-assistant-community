import type { Actions, PageServerLoad } from './$types';

import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { headData } from '$lib/utils/table';
import { fail, superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import { error, redirect } from '@sveltejs/kit';

interface RiskApprovalFlow {
	id: string;
	ref_id: string;
	status: string;
	risk_approval_stage: 'assessment' | 'treatment' | 'residual_acceptance';
	risk_approval_current: boolean;
	approver?: { email?: string } | null;
}

const EMPTY_APPROVAL_OPTIONS = {
	approvers: [],
	management_approvers: [],
	residual_risk_above_tolerance: false,
	risk_tolerance: -1,
	risk_tolerance_configured: false
};

export const load = (async ({ fetch, params, cookies, locals }) => {
	const URLModel = 'risk-scenarios';
	const baseEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;

	// Depends only on params.id, so start it now and let it overlap the fetches below.
	const riskAcceptancesPromise = fetchAllPages(
		fetch,
		`${BASE_API_URL}/risk-acceptances/?risk_scenarios=${params.id}`
	).catch(() => []);

	const res = await fetch(baseEndpoint);
	if (!res.ok) {
		if (res.status === 404) {
			// Check if focus mode is active
			const focusFolderId = cookies.get('focus_folder_id');
			const focusModeEnabled = locals.featureflags?.focus_mode ?? false;
			const isFocusModeActive = focusFolderId && focusModeEnabled;

			const message = isFocusModeActive
				? m.objectNotReachableFromCurrentFocus()
				: m.objectNotFound();
			setFlash({ type: 'warning', message }, cookies);
			throw redirect(302, '/risk-scenarios');
		}
		throw error(res.status, res.statusText || 'Failed to load risk scenario');
	}
	const scenario = await res.json();
	const object = await fetch(objectEndpoint).then((res) => res.json());

	const tables: Record<string, any> = {};

	await Promise.all(
		['assets', 'threats', 'vulnerabilities', 'security-exceptions'].map(async (key) => {
			const keyEndpoint = `${BASE_API_URL}/${key}/?risk_scenarios=${params.id}`;
			const response = await fetch(keyEndpoint);
			if (response.ok) {
				const table: TableSource = {
					head: headData(key),
					body: [],
					meta: []
				};
				tables[key] = table;
			} else {
				console.error(`Failed to fetch data for ${key}: ${response.statusText}`);
			}
		})
	);
	//todo the naming here is not great because of inverted logic inhereted from the filters
	await Promise.all(
		['risk_scenarios', 'risk_scenarios_e'].map(async (key) => {
			const table: TableSource = {
				head: headData('applied-controls'),
				body: [],
				meta: []
			};
			tables[key] = table;
		})
	);

	const riskMatrix = await fetch(`${BASE_API_URL}/risk-matrices/${object.risk_matrix}/`)
		.then((res) => res.json())
		.then((res) => JSON.parse(res.json_definition));

	const riskApprovalsEnabled = Boolean(
		locals.featureflags?.validation_flows && locals.featureflags?.risk_owner_approvals
	);
	const approvalOptionsPromise = riskApprovalsEnabled
		? fetch(`${baseEndpoint}approval-options/`).then((res) =>
				res.ok ? res.json() : EMPTY_APPROVAL_OPTIONS
			)
		: Promise.resolve(EMPTY_APPROVAL_OPTIONS);
	const riskApprovalsPromise = riskApprovalsEnabled
		? fetchAllPages<RiskApprovalFlow>(
				fetch,
				`${BASE_API_URL}/validation-flows/?risk_scenario=${params.id}`
			)
		: Promise.resolve([]);
	const [approvalOptions, riskApprovals] = await Promise.all([
		approvalOptionsPromise,
		riskApprovalsPromise
	]);

	return {
		scenario,
		approvalOptions,
		riskApprovals,
		tables,
		riskMatrix,
		title: scenario.str,
		riskAcceptances: await riskAcceptancesPromise
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	requestApproval: async (event) => {
		if (
			!event.locals.featureflags?.validation_flows ||
			!event.locals.featureflags?.risk_owner_approvals
		) {
			return fail(403, { approvalError: m.riskApprovalFeatureDisabled() });
		}
		const input = await event.request.formData();
		const parsed = z
			.object({
				approver: z.uuid(),
				stage: z.enum(['assessment', 'treatment', 'residual_acceptance']),
				notes: z.string().max(10000),
				deadline: z.union([z.literal(''), z.iso.date()])
			})
			.safeParse(Object.fromEntries(input));
		if (!parsed.success) return fail(400, { approvalError: m.riskApprovalInvalidRequest() });
		const scenarioResponse = await event.fetch(
			`${BASE_API_URL}/risk-scenarios/${event.params.id}/`
		);
		if (!scenarioResponse.ok)
			return fail(scenarioResponse.status, { approvalError: m.anErrorOccurred() });
		const scenario = await scenarioResponse.json();
		const response = await event.fetch(`${BASE_API_URL}/validation-flows/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				folder: scenario.folder.id,
				risk_scenario: event.params.id,
				risk_approval_stage: parsed.data.stage,
				approver: parsed.data.approver,
				request_notes: parsed.data.notes,
				validation_deadline: parsed.data.deadline || null
			})
		});
		if (!response.ok) {
			const { validationFlowErrorMessage } = await import('$lib/utils/validationFlows');
			return fail(response.status, {
				approvalError: validationFlowErrorMessage(await response.json()) ?? m.anErrorOccurred()
			});
		}
		setFlash({ type: 'success', message: m.riskApprovalRequested() }, event);
		return { approvalRequested: true };
	},
	syncToActions: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = z.object({ reset_residual: z.boolean().optional() });
		const form = await superValidate(formData, zod(schema));

		const response = await event.fetch(
			`${BASE_API_URL}/risk-scenarios/${event.params.id}/sync-to-actions/?dry_run=false`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(form.data)
			}
		);
		if (response.ok) {
			setFlash(
				{
					type: 'success',
					message: m.syncToAppliedControlsSuccess()
				},
				event
			);
		} else {
			setFlash(
				{
					type: 'error',
					message: m.syncToAppliedControlsError()
				},
				event
			);
		}
		return { form, message: { appliedControls: await response.json() } };
	}
};
