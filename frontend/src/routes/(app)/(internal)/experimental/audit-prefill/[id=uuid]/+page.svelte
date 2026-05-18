<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	$pageTitle = 'Audit Prefill — Review';

	const toast = getToastStore();

	let minConfidence = $state(0.7);
	let busy = $state(false);
	// Skip RAs already marked not_applicable when launching Wave 2. Defaults
	// on — N/A is an explicit auditor decision, re-scoring those just yields
	// no-op proposals the user has to dismiss.
	let skipNotApplicable = $state(true);
	// Two independent disclosures per action: the editor (pencil) and the
	// sources viewer ("N source passage(s)" link). One can be open without
	// the other, and they don't interfere — clicking pencil while sources
	// are open just adds the editor below.
	let editingAction = $state<string | null>(null);
	let viewingSourcesFor = $state<string | null>(null);
	let editedPayload = $state<Record<string, any>>({});

	// Poll while the run is active. Stops once status leaves queued/running.
	let pollHandle: ReturnType<typeof setInterval> | null = null;
	$effect(() => {
		const active = data.run?.status === 'queued' || data.run?.status === 'running';
		if (active && !pollHandle) {
			pollHandle = setInterval(() => {
				void invalidateAll();
			}, 2500);
		} else if (!active && pollHandle) {
			clearInterval(pollHandle);
			pollHandle = null;
		}
	});
	onDestroy(() => {
		if (pollHandle) clearInterval(pollHandle);
	});

	const wave = $derived(data.run?.config?.wave ?? 1);
	const parentRunId = $derived(data.run?.config?.parent_run_id ?? null);

	const wave1Kinds = ['extract_control', 'link_control_existing'];
	const wave2Kinds = ['propose_result'];

	const visibleActions = $derived(
		data.actions.filter((a: any) =>
			wave === 2 ? wave2Kinds.includes(a.kind) : wave1Kinds.includes(a.kind)
		)
	);
	const proposedCount = $derived(visibleActions.filter((a: any) => a.state === 'proposed').length);
	const approvedCount = $derived(visibleActions.filter((a: any) => a.state === 'approved').length);
	const rejectedCount = $derived(visibleActions.filter((a: any) => a.state === 'rejected').length);
	const wave1Settled = $derived(wave === 1 && proposedCount === 0 && visibleActions.length > 0);

	// Wave 1 breakdowns — used by the transparency banner so users can see
	// that dedup was done and Creates are the leftover "new" suggestions.
	const wave1CreateCount = $derived(
		visibleActions.filter((a: any) => a.kind === 'extract_control').length
	);
	const wave1LinkCount = $derived(
		visibleActions.filter((a: any) => a.kind === 'link_control_existing').length
	);
	const wave1CreateProposedCount = $derived(
		visibleActions.filter((a: any) => a.kind === 'extract_control' && a.state === 'proposed').length
	);
	const totalCandidatesExtracted = $derived(data.run?.config?.candidates ?? null);
	const existingFolderControlsCount = $derived(
		data.run?.config?.existing_folder_controls_count ?? null
	);

	// Wave 2 lookups: RA id → RA, AC id → AC.
	const raById = $derived(
		new Map<string, any>(data.requirementAssessments.map((ra: any) => [ra.id, ra]))
	);
	const acById = $derived(new Map<string, any>(data.appliedControls.map((ac: any) => [ac.id, ac])));

	function progressPct(): number {
		const t = data.run?.total_steps ?? 0;
		const c = data.run?.completed_steps ?? 0;
		if (!t) return 0;
		return Math.min(100, Math.round((c / t) * 100));
	}

	function statusBadge(s: string) {
		switch (s) {
			case 'queued':
			case 'running':
				return 'bg-yellow-100 text-yellow-800';
			case 'succeeded':
				return 'bg-green-100 text-green-800';
			case 'failed':
			case 'cancelled':
				return 'bg-red-100 text-red-800';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	}

	function actionStateBadge(s: string) {
		switch (s) {
			case 'proposed':
				return 'bg-blue-100 text-blue-800';
			case 'approved':
				return 'bg-green-100 text-green-800';
			case 'rejected':
				return 'bg-gray-200 text-gray-600';
			case 'expired':
				return 'bg-gray-100 text-gray-500 line-through';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	}

	function confidenceColor(c: number | null) {
		if (c === null || c === undefined) return 'text-gray-400';
		if (c >= 0.8) return 'text-green-700';
		if (c >= 0.6) return 'text-amber-700';
		return 'text-red-700';
	}

	function resultBadge(r: string) {
		switch (r) {
			case 'compliant':
				return 'bg-green-100 text-green-800';
			case 'partially_compliant':
				return 'bg-amber-100 text-amber-800';
			case 'non_compliant':
				return 'bg-red-100 text-red-800';
			case 'not_applicable':
				return 'bg-gray-200 text-gray-600';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	}

	async function callOp(body: any): Promise<any> {
		const res = await fetch(`/experimental/audit-prefill/${data.run.id}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		const data2 = await res.json().catch(() => ({}));
		if (!res.ok) {
			toast.trigger({ message: data2.detail || 'Request failed.' });
			throw new Error(data2.detail || 'Request failed.');
		}
		return data2;
	}

	function toggleEdit(actionId: string, current: any) {
		if (editingAction === actionId) {
			editingAction = null;
			return;
		}
		editingAction = actionId;
		// Seed editable fields based on kind.
		if (current.kind === 'extract_control') {
			editedPayload = {
				name: current.payload?.name ?? '',
				description: current.payload?.description ?? '',
				category: current.payload?.category ?? '',
				csf_function: current.payload?.csf_function ?? ''
			};
		} else if (current.kind === 'propose_result') {
			editedPayload = {
				result: current.payload?.result ?? 'not_assessed',
				observation: current.payload?.observation ?? ''
			};
		} else {
			editedPayload = {};
		}
	}

	function toggleSources(actionId: string) {
		viewingSourcesFor = viewingSourcesFor === actionId ? null : actionId;
	}

	async function approveAction(action: any) {
		if (busy) return;
		busy = true;
		try {
			let overridePayload: any = undefined;
			if (editingAction === action.id) {
				if (action.kind === 'extract_control') {
					overridePayload = editedPayload;
				} else if (action.kind === 'propose_result') {
					overridePayload = {
						result: editedPayload.result,
						observation: editedPayload.observation
					};
				}
			}
			await callOp({ op: 'approve', actionId: action.id, payload: overridePayload });
			toast.trigger({ message: 'Approved.' });
			editingAction = null;
			viewingSourcesFor = null;
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	async function rejectAction(action: any) {
		if (busy) return;
		busy = true;
		try {
			await callOp({ op: 'reject', actionId: action.id });
			toast.trigger({ message: 'Rejected.' });
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	async function bulkApprove() {
		if (busy) return;
		busy = true;
		try {
			const res = await callOp({
				op: 'bulk-approve',
				minConfidence,
				kinds: wave === 2 ? wave2Kinds : wave1Kinds
			});
			toast.trigger({
				message: `Approved ${res.approved}. ${res.remaining_proposed} still proposed.`
			});
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	async function bulkReject(opts: { kinds?: string[]; label: string }) {
		if (busy) return;
		if (
			!confirm(
				`${opts.label}? They'll be marked rejected and excluded from the catalog (no destructive side effects — you can still re-run if needed).`
			)
		) {
			return;
		}
		busy = true;
		try {
			const res = await callOp({ op: 'bulk-reject', kinds: opts.kinds });
			toast.trigger({
				message: `Rejected ${res.rejected}. ${res.remaining_proposed} still proposed.`
			});
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	async function startWave2() {
		if (busy) return;
		busy = true;
		try {
			const res = await callOp({
				op: 'start-wave2',
				skip_not_applicable: skipNotApplicable
			});
			toast.trigger({ message: 'Wave 2 started.' });
			await goto(`/experimental/audit-prefill/${res.id}`);
		} finally {
			busy = false;
		}
	}

	async function cancelRun() {
		if (busy) return;
		busy = true;
		try {
			await callOp({ op: 'cancel' });
			toast.trigger({ message: 'Run cancelled.' });
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	async function deleteRun() {
		if (busy) return;
		const label = data.complianceAssessment?.str || `run ${data.run.id.slice(0, 8)}`;
		if (
			!confirm(
				`Delete this prefill run for "${label}"? Removes the agent's audit trail (proposals + decisions). Created applied controls and approved RA verdicts stay.`
			)
		) {
			return;
		}
		busy = true;
		try {
			const res = await fetch(`/experimental/audit-prefill/${data.run.id}`, {
				method: 'DELETE'
			});
			if (res.status === 204 || res.ok) {
				toast.trigger({ message: 'Run deleted.' });
				await goto('/experimental/audit-prefill');
			} else {
				const err = await res.json().catch(() => ({}));
				toast.trigger({ message: err.detail || 'Failed to delete the run.' });
			}
		} finally {
			busy = false;
		}
	}

	function controlName(controlId: string): string {
		const inCatalog = acById.get(controlId);
		if (inCatalog) return inCatalog.str || inCatalog.name || controlId;
		return controlId;
	}
</script>

<div class="space-y-4">
	<!-- Header -->
	<div class="bg-white shadow-sm py-4 px-6 card">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h4 class="h4 font-bold">
					<i class="fa-solid fa-wand-magic-sparkles mr-2"></i>Audit Prefill — Wave {wave}
				</h4>
				<div class="text-sm text-gray-600 mt-1">
					<span class="font-mono">{data.complianceAssessment?.str || '—'}</span>
					<span class="text-gray-400 mx-1">·</span>
					<span>{data.complianceAssessment?.framework?.str || ''}</span>
					<span class="text-gray-400 mx-1">·</span>
					<span>{data.run.folder?.str || data.run.folder?.name}</span>
				</div>
				<div class="text-xs text-gray-500 mt-1">
					Strictness: <span class="font-semibold">{data.run.strictness}</span>
					&nbsp;·&nbsp; Model: {data.run.model_used || '—'}
					&nbsp;·&nbsp; Tokens: {data.run.total_tokens ?? 0}
					{#if parentRunId}
						&nbsp;·&nbsp;
						<a
							href="/experimental/audit-prefill/{parentRunId}"
							class="text-pink-600 hover:underline"
						>
							← back to Wave 1
						</a>
					{/if}
				</div>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<span class="text-xs px-2 py-1 rounded {statusBadge(data.run.status)}">
					{data.run.status}
				</span>
				{#if data.run.status === 'queued' || data.run.status === 'running'}
					<button
						type="button"
						class="btn preset-outlined text-xs"
						onclick={cancelRun}
						disabled={busy}
						title="Cancel this run. Worker checks before each step."
					>
						<i class="fa-solid fa-stop mr-1"></i>Cancel
					</button>
				{/if}
				<button
					type="button"
					class="btn preset-outlined text-xs text-red-700 hover:bg-red-50"
					onclick={deleteRun}
					disabled={busy || data.run.status === 'running'}
					title={data.run.status === 'running'
						? 'Cancel the run first, then delete.'
						: 'Delete this run + its proposals.'}
				>
					<i class="fa-solid fa-trash mr-1"></i>Delete
				</button>
			</div>
		</div>
		{#if data.run.status === 'running'}
			<div class="mt-3">
				<div class="flex justify-between text-xs text-gray-500 mb-1">
					<span class="truncate">{data.run.current_step_label || 'Working…'}</span>
					<span>{data.run.completed_steps ?? 0}/{data.run.total_steps ?? 0}</span>
				</div>
				<div class="w-full bg-gray-200 rounded-full h-2">
					<div
						class="bg-pink-500 h-2 rounded-full transition-all"
						style="width: {progressPct()}%"
					></div>
				</div>
			</div>
		{:else if data.run.status === 'failed'}
			<p class="mt-2 text-xs text-red-700 whitespace-pre-wrap">{data.run.error_message}</p>
		{/if}
	</div>

	<!-- Tabs -->
	<div class="bg-white shadow-sm card">
		<div class="border-b border-gray-200 px-6 pt-4 flex gap-6">
			{#if wave === 1}
				<button
					type="button"
					class="pb-3 px-1 text-sm font-medium border-b-2 border-pink-500 text-pink-700"
				>
					Controls
					<span class="ml-1 text-xs text-gray-500">({visibleActions.length})</span>
				</button>
				<button
					type="button"
					class="pb-3 px-1 text-sm font-medium border-b-2 border-transparent text-gray-400 cursor-not-allowed"
					disabled
					title={wave1Settled
						? 'Click "Start Wave 2" below to move on.'
						: 'Approve or reject every Wave 1 proposal first.'}
				>
					Requirements
					<i class="fa-solid fa-lock ml-1 text-xs"></i>
				</button>
			{:else}
				<a
					href={parentRunId ? `/experimental/audit-prefill/${parentRunId}` : '#'}
					class="pb-3 px-1 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700"
				>
					Controls
				</a>
				<button
					type="button"
					class="pb-3 px-1 text-sm font-medium border-b-2 border-pink-500 text-pink-700"
				>
					Requirements
					<span class="ml-1 text-xs text-gray-500">({visibleActions.length})</span>
				</button>
			{/if}
		</div>

		<div class="p-6 space-y-3">
			{#if wave === 1 && existingFolderControlsCount !== null && (data.run.status === 'queued' || data.run.status === 'running' || visibleActions.length === 0)}
				<!-- Upfront context banner: shown while Wave 1 has no proposals to
					display yet, so the user knows the perimeter is being tracked
					and will flow into Wave 2. -->
				<div class="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-900">
					<i class="fa-solid fa-database mr-1 text-blue-500"></i>
					<strong>{existingFolderControlsCount}</strong> existing control{existingFolderControlsCount ===
					1
						? ''
						: 's'} found in this folder. Carried as context into Wave 2.
				</div>
			{/if}
			{#if data.run.status === 'queued'}
				<p class="text-sm text-gray-500 italic">Run is queued — waiting for a worker.</p>
			{:else if visibleActions.length === 0}
				<p class="text-sm text-gray-500 italic">
					{#if data.run.status === 'running'}
						{wave === 2
							? 'Asking the LLM for a verdict on each requirement…'
							: 'Reading documents and clustering candidates…'}
					{:else if data.run.status === 'succeeded'}
						{wave === 2
							? 'No requirement proposals — the audit may have no selected requirements, or every result was unchanged from current state.'
							: 'No control candidates extracted. The folder may not contain readable security docs.'}
					{:else}
						Run is not active.
					{/if}
				</p>
			{:else}
				{#if data.run.status === 'running'}
					<!-- Live banner: tells the user proposals are streaming in. The
						bulk action bar below is rendered but disabled until the run
						finishes — the set isn't final yet. -->
					<div
						class="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-900 flex items-center gap-2"
					>
						<i class="fa-solid fa-spinner fa-spin text-amber-600"></i>
						<span>
							{wave === 2 ? 'Drafting verdicts' : 'Drafting controls'} live —
							<strong>{visibleActions.length}</strong> so far. New entries appear as the agent processes
							them. Bulk actions unlock when the run finishes.
						</span>
					</div>
				{/if}
				{#if wave === 1}
					<!-- Transparency banner: explains what Wave 1 actually did so the
						user sees that Create proposals are leftovers AFTER dedup, and
						that the existing folder controls are known and will flow into
						Wave 2 as context for per-requirement scoring. -->
					<div
						class="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-900 space-y-1"
					>
						<div>
							<i class="fa-solid fa-circle-info mr-1 text-blue-600"></i>
							{#if totalCandidatesExtracted !== null}
								Wave 1 extracted <strong>{totalCandidatesExtracted}</strong> candidate control{totalCandidatesExtracted ===
								1
									? ''
									: 's'}
								from your documents and deduped them against existing perimeter controls.
							{:else}
								Wave 1 deduped the extracted candidates against existing perimeter controls.
							{/if}
							Result:
							<span class="px-1.5 py-0.5 rounded bg-cyan-100 text-cyan-800 mx-1">
								{wave1LinkCount} Link
							</span>
							(matches an existing control — no new entry needed) and
							<span class="px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 mx-1">
								{wave1CreateCount} Create
							</span>
							(new control we'd like to add).
							{#if wave1CreateCount > 0}
								The Creates are <em>extra</em> on top of what you already have — review them carefully,
								or use "Ignore new suggestions" below to dismiss them all.
							{/if}
						</div>
						{#if existingFolderControlsCount !== null}
							<div class="text-xs text-blue-800">
								<i class="fa-solid fa-database mr-1 text-blue-500"></i>
								<strong>{existingFolderControlsCount}</strong> existing control{existingFolderControlsCount ===
								1
									? ''
									: 's'} found in this folder. Wave 2 will consider {existingFolderControlsCount ===
								1
									? 'it'
									: 'them'} (minus any approved as Link above) as additional context when scoring each
								requirement.
							</div>
						{/if}
					</div>
				{/if}

				<!-- Bulk action bar -->
				<div
					class="flex flex-col md:flex-row md:items-start md:justify-between gap-3 bg-gray-50 rounded p-3 text-sm"
				>
					<div class="space-x-2">
						<span class="font-semibold">Wave {wave} summary:</span>
						<span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800">
							{proposedCount} proposed
						</span>
						<span class="px-2 py-0.5 rounded bg-green-100 text-green-800">
							{approvedCount} approved
						</span>
						<span class="px-2 py-0.5 rounded bg-gray-200 text-gray-600">
							{rejectedCount} rejected
						</span>
					</div>
					<div class="flex flex-col items-stretch md:items-end gap-2">
						<div class="flex items-center gap-2">
							<label class="text-xs text-gray-600">Min confidence</label>
							<input
								type="number"
								min="0"
								max="1"
								step="0.05"
								bind:value={minConfidence}
								class="w-20 rounded border-gray-300 text-sm"
								disabled={busy}
							/>
							<button
								type="button"
								class="btn preset-filled text-sm"
								onclick={bulkApprove}
								disabled={busy || proposedCount === 0 || data.run.status === 'running'}
								title={data.run.status === 'running'
									? 'Wait for the run to finish — the proposal set is still streaming in.'
									: 'Approve every proposal at or above this confidence.'}
							>
								<i class="fa-solid fa-check mr-1"></i>
								Approve all ≥ {Math.round(minConfidence * 100)}%
							</button>
						</div>
						<div class="flex items-center gap-2">
							{#if wave === 1 && wave1CreateProposedCount > 0}
								<button
									type="button"
									class="btn preset-outlined text-xs text-red-700 hover:bg-red-50"
									onclick={() =>
										bulkReject({
											kinds: ['extract_control'],
											label: `Ignore all ${wave1CreateProposedCount} new (Create) suggestion(s)`
										})}
									disabled={busy || data.run.status === 'running'}
									title={data.run.status === 'running'
										? 'Wait for the run to finish before bulk-rejecting.'
										: "Reject every 'Create' proposal that's still proposed. Link-to-existing proposals are untouched."}
								>
									<i class="fa-solid fa-xmark mr-1"></i>
									Ignore {wave1CreateProposedCount} new suggestion{wave1CreateProposedCount === 1
										? ''
										: 's'}
								</button>
							{/if}
							<button
								type="button"
								class="btn preset-outlined text-xs text-red-700 hover:bg-red-50"
								onclick={() =>
									bulkReject({
										label: `Reject all ${proposedCount} remaining proposal(s)`
									})}
								disabled={busy || proposedCount === 0 || data.run.status === 'running'}
								title={data.run.status === 'running'
									? 'Wait for the run to finish before bulk-rejecting.'
									: "Reject every proposal that's still in the proposed state."}
							>
								<i class="fa-solid fa-xmark mr-1"></i>
								Reject all {proposedCount} remaining
							</button>
						</div>
					</div>
				</div>

				{#if wave === 1 && wave1Settled}
					<div
						class="bg-pink-50 border border-pink-200 rounded p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
					>
						<div class="text-sm text-pink-900">
							Wave 1 fully resolved.
							<span class="text-pink-700">{approvedCount} controls in the catalog;</span>
							ready to start the per-requirement pass.
						</div>
						<div class="flex flex-col md:items-end gap-2">
							<label class="flex items-center gap-2 text-xs text-pink-900 cursor-pointer">
								<input
									type="checkbox"
									bind:checked={skipNotApplicable}
									class="rounded border-pink-300"
									disabled={busy}
								/>
								<span>
									Skip requirements already marked
									<code class="px-1 py-0.5 rounded bg-pink-100 text-pink-700">not_applicable</code>
								</span>
							</label>
							<button type="button" class="btn preset-filled" onclick={startWave2} disabled={busy}>
								<i class="fa-solid fa-forward mr-2"></i>Start Wave 2
							</button>
						</div>
					</div>
				{/if}

				<!-- Proposals list -->
				<ul class="space-y-2">
					{#each visibleActions as action}
						{@const isEditing = editingAction === action.id}
						{@const isViewingSources = viewingSourcesFor === action.id}
						{@const ra =
							action.kind === 'propose_result' && action.target_object_id
								? raById.get(action.target_object_id)
								: null}
						<li class="border rounded p-3 hover:shadow-sm transition-shadow">
							<div class="flex justify-between items-start gap-3">
								<div class="flex-1 min-w-0">
									<!-- Kind / state / confidence row -->
									<div class="flex items-center gap-2 mb-1">
										{#if action.kind === 'extract_control'}
											<span class="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
												<i class="fa-solid fa-plus mr-1"></i>Create
											</span>
										{:else if action.kind === 'link_control_existing'}
											<span class="text-xs px-1.5 py-0.5 rounded bg-cyan-100 text-cyan-800">
												<i class="fa-solid fa-link mr-1"></i>Link existing
											</span>
										{:else if action.kind === 'propose_result'}
											{#if action.payload?.current_result && action.payload?.current_result !== action.payload?.result}
												<span
													class="text-xs px-1.5 py-0.5 rounded {resultBadge(
														action.payload?.current_result
													)} opacity-60"
													title="Current state of this requirement"
												>
													{action.payload?.current_result}
												</span>
												<i class="fa-solid fa-arrow-right text-[10px] text-gray-400"></i>
											{/if}
											<span
												class="text-xs px-1.5 py-0.5 rounded {resultBadge(action.payload?.result)}"
												title={action.payload?.current_result &&
												action.payload?.current_result !== action.payload?.result
													? 'Proposed new state'
													: 'Proposed state'}
											>
												{action.payload?.result ?? 'not_assessed'}
											</span>
										{/if}
										<span class="text-xs px-1.5 py-0.5 rounded {actionStateBadge(action.state)}">
											{action.state}
										</span>
										<span class="text-xs {confidenceColor(action.confidence)}">
											{action.confidence !== null && action.confidence !== undefined
												? `${Math.round(action.confidence * 100)}%`
												: '—'}
										</span>
									</div>

									<!-- Header line, kind-dependent -->
									{#if action.kind === 'propose_result'}
										<div class="text-sm font-semibold truncate">
											{ra
												? `${ra.requirement?.ref_id ?? ''} ${ra.requirement?.str ?? ra.requirement?.name ?? ''}`.trim()
												: (action.target_object_id ?? '(missing requirement)')}
										</div>
										{#if action.payload?.control_ids?.length}
											<div class="text-xs text-gray-600 mt-1">
												<span class="font-medium">Controls cited:</span>
												{action.payload.control_ids
													.map((cid: string) => controlName(cid))
													.join(', ')}
											</div>
										{:else}
											<div class="text-xs text-gray-400 italic mt-1">No controls cited.</div>
										{/if}
										{#if action.payload?.observation}
											<div class="text-xs text-gray-700 mt-1 line-clamp-2">
												{action.payload.observation}
											</div>
										{/if}
									{:else}
										<div class="text-sm font-semibold truncate">
											{action.payload?.name ||
												action.payload?.candidate_name ||
												action.payload?.existing_control_name ||
												'(no name)'}
										</div>
										{#if action.payload?.description || action.payload?.candidate_description}
											<div class="text-xs text-gray-600 mt-0.5">
												{action.payload?.description || action.payload?.candidate_description}
											</div>
										{/if}
										{#if action.kind === 'link_control_existing' && action.payload?.existing_control_name}
											<div class="text-xs text-gray-500 mt-1">
												<i class="fa-solid fa-arrow-right mx-1"></i>
												linking to:
												<span class="font-mono">{action.payload.existing_control_name}</span>
											</div>
										{/if}
									{/if}

									{#if action.rationale}
										<div class="text-xs text-gray-500 italic mt-1 line-clamp-2">
											{action.rationale}
										</div>
									{/if}
									{#if action.source_refs?.length > 0}
										<button
											type="button"
											class="text-xs text-pink-600 hover:underline mt-1"
											onclick={() => toggleSources(action.id)}
										>
											{isViewingSources ? 'Hide' : 'Show'}
											{action.source_refs.length} source passage{action.source_refs.length === 1
												? ''
												: 's'}
										</button>
									{/if}
								</div>

								{#if action.state === 'proposed'}
									<div class="flex gap-1 shrink-0">
										{#if action.kind === 'extract_control' || action.kind === 'propose_result'}
											<button
												type="button"
												class="btn preset-outlined text-xs"
												onclick={() => toggleEdit(action.id, action)}
												disabled={busy}
												title={isEditing ? 'Hide editor' : 'Edit before approving'}
											>
												<i class="fa-solid fa-pencil"></i>
											</button>
										{/if}
										<button
											type="button"
											class="btn preset-filled text-xs"
											onclick={() => approveAction(action)}
											disabled={busy}
										>
											<i class="fa-solid fa-check"></i>
										</button>
										<button
											type="button"
											class="btn preset-outlined text-xs"
											onclick={() => rejectAction(action)}
											disabled={busy}
										>
											<i class="fa-solid fa-xmark"></i>
										</button>
									</div>
								{/if}
							</div>

							{#if isEditing}
								<div
									class="mt-3 pt-3 border-t border-gray-200 bg-amber-50/40 -mx-3 -mb-3 px-3 pb-3 rounded-b"
								>
									<div class="text-xs font-semibold uppercase tracking-wide text-amber-800 mb-2">
										<i class="fa-solid fa-pencil mr-1"></i>Edit before approving
									</div>
									{#if action.kind === 'extract_control'}
										<div class="grid grid-cols-2 gap-3">
											<label class="block text-xs">
												<span class="font-medium text-gray-700 block mb-1">Name</span>
												<input
													type="text"
													bind:value={editedPayload.name}
													maxlength="200"
													class="w-full text-sm rounded border-gray-300"
												/>
											</label>
											<label class="block text-xs">
												<span class="font-medium text-gray-700 block mb-1">Category</span>
												<select
													bind:value={editedPayload.category}
													class="w-full text-sm rounded border-gray-300"
												>
													<option value="">—</option>
													<option value="policy">policy</option>
													<option value="process">process</option>
													<option value="technical">technical</option>
													<option value="physical">physical</option>
													<option value="procedure">procedure</option>
												</select>
											</label>
											<label class="block text-xs col-span-2">
												<span class="font-medium text-gray-700 block mb-1">Description</span>
												<textarea
													bind:value={editedPayload.description}
													rows="2"
													class="w-full text-sm rounded border-gray-300"
												></textarea>
											</label>
											<label class="block text-xs">
												<span class="font-medium text-gray-700 block mb-1">CSF function</span>
												<select
													bind:value={editedPayload.csf_function}
													class="w-full text-sm rounded border-gray-300"
												>
													<option value="">—</option>
													<option value="govern">govern</option>
													<option value="identify">identify</option>
													<option value="protect">protect</option>
													<option value="detect">detect</option>
													<option value="respond">respond</option>
													<option value="recover">recover</option>
												</select>
											</label>
										</div>
									{:else if action.kind === 'propose_result'}
										<div class="space-y-3">
											<label class="block text-xs">
												<span class="font-medium text-gray-700 block mb-1">Result</span>
												<select
													bind:value={editedPayload.result}
													class="w-full text-sm rounded border-gray-300"
												>
													<option value="compliant">compliant</option>
													<option value="partially_compliant">partially_compliant</option>
													<option value="non_compliant">non_compliant</option>
													<option value="not_applicable">not_applicable</option>
												</select>
											</label>
											<label class="block text-xs">
												<span class="font-medium text-gray-700 block mb-1">Observation</span>
												<textarea
													bind:value={editedPayload.observation}
													rows="3"
													class="w-full text-sm rounded border-gray-300"
												></textarea>
											</label>
											{#if action.payload?.evidence_links?.length}
												<div class="text-xs text-gray-500">
													On approval, each cited control will be linked to
													{action.payload.evidence_links[0]?.evidence_ids?.length ?? 0}
													evidence(s).
												</div>
											{/if}
										</div>
									{/if}
								</div>
							{/if}

							{#if isViewingSources && action.source_refs?.length > 0}
								<div
									class="mt-3 pt-3 border-t border-gray-200 bg-gray-50/60 -mx-3 -mb-3 px-3 pb-3 rounded-b"
								>
									<div class="text-xs font-semibold uppercase tracking-wide text-gray-600 mb-2">
										<i class="fa-solid fa-quote-left mr-1"></i>Sources
									</div>
									<ul class="space-y-1.5">
										{#each action.source_refs as ref}
											<li class="text-xs bg-white border border-gray-200 rounded p-2">
												<div class="font-mono text-gray-700">
													[{ref.index}] {ref.name}
												</div>
												{#if ref.snippet}
													<div class="text-gray-600 mt-1 italic">
														"{ref.snippet}"
													</div>
												{/if}
											</li>
										{/each}
									</ul>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</div>
</div>
