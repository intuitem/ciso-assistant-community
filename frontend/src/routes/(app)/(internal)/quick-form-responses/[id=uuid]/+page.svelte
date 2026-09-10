<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import Question from '$lib/components/Forms/Question.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { canPerformActionOnObject } from '$lib/utils/access-control';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const toastStore = getToastStore();

	const response = $derived(data.response);
	const content = $derived(data.content);
	const visiblePages = $derived((content.pages ?? []).filter((p: any) => !p.hidden));

	let pageIndex = $state(0);
	$effect(() => {
		if (pageIndex > visiblePages.length - 1) pageIndex = Math.max(0, visiblePages.length - 1);
	});
	const currentPage = $derived(visiblePages[pageIndex]);

	const canEdit = $derived(
		canPerformActionOnObject({
			user: page.data.user,
			action: 'change',
			model: 'quickformresponse',
			object: response
		})
	);
	const viewerIsRequester = $derived(!!data.viewerIsRequester);
	const suggestedActions = $derived((data.suggestedActions ?? []) as any[]);

	// "Why can't I submit?" has to be answerable from the screen. The server resolves
	// visibility, so it tells us which required questions are still blank.
	const missingRequired = $derived(
		((content.missing_required ?? []) as string[]).map((urn) => {
			for (const page of content.pages ?? []) {
				const q = page.questions?.[urn];
				if (q) return { urn, page: page.name, text: q.text || urn };
			}
			return { urn, page: '', text: urn };
		})
	);
	// A requester edits their own draft; a reviewer edits by folder permission.
	const canEditAnswers = $derived((viewerIsRequester || canEdit) && content.can_edit_answers);

	let busy = $state(false);
	let reopenObservation = $state('');

	async function post(action: string, body: Record<string, unknown>) {
		busy = true;
		try {
			const res = await fetch(`?/${action}`, {
				method: 'POST',
				body: JSON.stringify({ id: response.id, ...body })
			});
			const result = await res.json();
			// SvelteKit wraps action data; the backend status travels in the body.
			const payload = result?.data ? JSON.parse(result.data) : null;
			const status = Array.isArray(payload) ? payload[payload[0]?.status] : null;
			if (!res.ok || (typeof status === 'number' && status >= 400)) {
				const detail = Array.isArray(payload) ? payload[payload[0]?.body] : null;
				const errorKey = detail && typeof detail === 'object' ? Object.values(detail)[0] : null;
				toastStore.trigger({
					message: safeTranslate(String(errorKey ?? 'anErrorOccurred')),
					background: 'preset-filled-error-500'
				});
			}
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	async function saveAnswer(urn: string, value: unknown) {
		await post('updateAnswers', { answers: { [urn]: value } });
	}

	const statusColor: Record<string, string> = {
		in_progress: 'preset-filled-primary-500',
		submitted: 'preset-filled-warning-500',
		closed: 'preset-filled-success-500'
	};
</script>

<div class="max-w-4xl mx-auto space-y-4 p-4">
	<div class="card bg-surface-50-950 shadow-sm p-4 space-y-3">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="min-w-0">
				<h1 class="text-xl font-semibold truncate">{response.name}</h1>
				<p class="text-sm text-surface-500">
					<a class="anchor" href="/quick-forms/{response.quick_form?.id}">
						{response.quick_form?.str ?? content.quick_form?.name}
					</a>
					· {response.folder?.str}
				</p>
			</div>
			<span class="badge {statusColor[response.status] ?? 'preset-filled-surface-500'}">
				{safeTranslate(response.status)}
			</span>
		</div>

		{#if content.quick_form?.description}
			<MarkdownRenderer content={content.quick_form.description} class="text-sm" />
		{/if}

		<div class="flex flex-wrap items-center gap-4 text-sm">
			{#if response.ref_id}
				<span class="font-mono text-surface-500">{response.ref_id}</span>
			{/if}
			<span>
				<i class="fa-solid fa-list-check mr-1 text-surface-500"></i>
				{m.quickFormAnsweredProgress({
					answered: content.progress?.answered_count ?? 0,
					total: content.progress?.total_count ?? 0
				})}
			</span>
			{#if content.score !== null && content.score !== undefined}
				<span
					><i class="fa-solid fa-star mr-1 text-surface-500"></i>{m.score()}: {content.score}</span
				>
			{/if}
			{#if content.hidden_pages?.length}
				<span class="text-surface-500"
					><i class="fa-solid fa-eye-slash mr-1"></i>{m.quickFormHiddenPagesHint()}</span
				>
			{/if}
		</div>

		{#if canEditAnswers && missingRequired.length}
			<aside
				class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40"
			>
				<div class="font-medium text-amber-900 dark:text-amber-200">
					<i class="fa-solid fa-circle-exclamation mr-1"></i>
					{m.quickFormMissingRequired({ count: missingRequired.length })}
				</div>
				<ul class="mt-1 list-inside list-disc text-xs text-amber-800 dark:text-amber-300">
					{#each missingRequired as q (q.urn)}
						<li>
							{q.text}{#if q.page}<span class="text-amber-600 dark:text-amber-400">
									&nbsp;— {q.page}</span
								>{/if}
						</li>
					{/each}
				</ul>
			</aside>
		{/if}

		{#if canEditAnswers}
			<p class="text-xs text-surface-500">
				<i class="fa-solid fa-cloud-arrow-up mr-1"></i>
				{response.ref_id
					? m.quickFormDraftSavedWithRef({ ref: response.ref_id })
					: m.quickFormDraftSaved()}
			</p>
		{/if}

		{#if content.computed_outcome && Object.keys(content.computed_outcome).length > 0}
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-xs font-semibold uppercase tracking-wider text-surface-500"
					>{m.computedOutcomes()}</span
				>
				{#each Object.entries(content.computed_outcome) as [refId, payload]}
					<span
						class="badge preset-tonal"
						style={(payload as any)?.color ? `background:${(payload as any).color}` : ''}
					>
						{(payload as any)?.label ?? (payload as any)?.annotation ?? refId}
					</span>
				{/each}
			</div>
		{/if}

		{#if response.observation && response.status === 'draft'}
			<div
				class="rounded-lg border border-warning-300 bg-warning-50 dark:bg-warning-500/10 p-3 text-sm"
			>
				<span class="font-semibold">{m.quickFormReviewerObservation()}:</span>
				{response.observation}
			</div>
		{/if}

		{#if viewerIsRequester}
			<!-- The person who filed this. Submitting is theirs; deciding is not. -->
			<div class="flex flex-wrap items-center gap-2 pt-1">
				{#if response.status === 'draft'}
					<button
						type="button"
						class="btn btn-sm preset-filled-success-500"
						disabled={busy || !content.progress?.complete}
						title={content.progress?.complete ? m.quickFormComplete() : m.quickFormIncomplete()}
						onclick={() => post('setStatus', { status: 'submitted' })}
					>
						<i class="fa-solid fa-paper-plane mr-1"></i>{m.quickFormSubmit()}
					</button>
				{:else if response.status === 'submitted' || response.status === 'in_review'}
					<button
						type="button"
						class="btn btn-sm preset-outlined-warning-500"
						disabled={busy}
						onclick={() => post('drop', { observation: null })}
					>
						<i class="fa-solid fa-ban mr-1"></i>{m.quickFormDrop()}
					</button>
				{/if}
				<button
					type="button"
					class="btn btn-sm preset-tonal"
					disabled={busy}
					onclick={() => post('clone', {})}
				>
					<i class="fa-solid fa-copy mr-1"></i>{m.quickFormClone()}
				</button>
			</div>
		{:else if canEdit}
			{#if suggestedActions.length}
				<!-- Supervised automation: the outcomes suggest, the reviewer commits, the
				     workflow executes. Offered only when the answers make them relevant. -->
				<div class="flex flex-wrap items-center gap-2 pt-1">
					<span class="text-xs font-semibold uppercase tracking-wider text-surface-500">
						{m.quickFormSuggestedActions()}
					</span>
					{#each suggestedActions as sa (sa.version)}
						<button
							type="button"
							class="btn btn-sm preset-tonal-primary"
							disabled={busy}
							title={sa.because
								? m.quickFormActionBecause({ outcome: sa.because })
								: (sa.description ?? '')}
							onclick={() => post('runAction', { version: sa.version })}
						>
							<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{sa.label}
						</button>
					{/each}
				</div>
			{/if}
			<!-- The reviewer. Claiming is optional; a decision always carries a resolution. -->
			<div class="flex flex-wrap items-center gap-2 pt-1">
				{#if response.status === 'draft'}
					<button
						type="button"
						class="btn btn-sm preset-filled-success-500"
						disabled={busy || !content.progress?.complete}
						title={content.progress?.complete ? m.quickFormComplete() : m.quickFormIncomplete()}
						onclick={() => post('setStatus', { status: 'submitted' })}
					>
						<i class="fa-solid fa-paper-plane mr-1"></i>{m.quickFormSubmit()}
					</button>
				{/if}
				{#if response.status === 'submitted'}
					<button
						type="button"
						class="btn btn-sm preset-tonal-primary"
						disabled={busy}
						onclick={() => post('setStatus', { status: 'in_review' })}
					>
						<i class="fa-solid fa-hand mr-1"></i>{m.quickFormClaim()}
					</button>
				{/if}
				{#if response.status === 'in_review' && response.assignee}
					<span class="text-sm text-surface-500">
						<i class="fa-solid fa-user-check mr-1"></i>{response.assignee.str}
					</span>
				{/if}
				{#if response.status === 'submitted' || response.status === 'in_review'}
					<input
						type="text"
						class="input max-w-xs text-sm"
						placeholder={m.quickFormReopenPrompt()}
						bind:value={reopenObservation}
					/>
					<button
						type="button"
						class="btn btn-sm preset-outlined-warning-500"
						disabled={busy}
						onclick={() =>
							post('setStatus', { status: 'draft', observation: reopenObservation || null })}
					>
						<i class="fa-solid fa-rotate-left mr-1"></i>{m.quickFormRequestChanges()}
					</button>
					<button
						type="button"
						class="btn btn-sm preset-filled-success-500"
						disabled={busy}
						onclick={() =>
							post('setStatus', {
								status: 'closed',
								resolution: 'accepted',
								observation: reopenObservation || null
							})}
					>
						<i class="fa-solid fa-check mr-1"></i>{m.quickFormAccept()}
					</button>
					<button
						type="button"
						class="btn btn-sm preset-outlined-error-500"
						disabled={busy}
						onclick={() =>
							post('setStatus', {
								status: 'closed',
								resolution: 'rejected',
								observation: reopenObservation || null
							})}
					>
						<i class="fa-solid fa-xmark mr-1"></i>{m.quickFormReject()}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	{#if visiblePages.length === 0}
		<div class="card bg-surface-50-950 shadow-sm p-6 text-center text-surface-500">
			{m.quickFormNoPages()}
		</div>
	{:else}
		<!-- Stepper -->
		<ol class="flex flex-wrap items-center gap-2 text-sm">
			{#each visiblePages as p, i (p.urn)}
				<li>
					<button
						type="button"
						class="px-3 py-1 rounded-full border transition-colors {i === pageIndex
							? 'bg-primary-500 text-white border-primary-500'
							: 'border-surface-300-700 hover:border-primary-300'}"
						onclick={() => (pageIndex = i)}
					>
						{i + 1}. {p.name || p.ref_id}
					</button>
				</li>
			{/each}
		</ol>

		{#if currentPage}
			{#key currentPage.urn}
				<div class="card bg-surface-50-950 shadow-sm p-4 space-y-4">
					<div>
						<h2 class="text-lg font-semibold">{currentPage.name}</h2>
						{#if currentPage.description}
							<MarkdownRenderer content={currentPage.description} class="text-sm mt-1" />
						{/if}
					</div>
					{#if !canEditAnswers}
						<p class="text-xs text-surface-500">{m.quickFormReadOnly()}</p>
					{/if}
					<Question
						questions={currentPage.questions ?? {}}
						initialValue={content.answers ?? {}}
						field="answers"
						disabled={!canEditAnswers}
						onChange={saveAnswer}
					/>
				</div>
			{/key}

			<div class="flex items-center justify-between">
				<button
					type="button"
					class="btn preset-outlined-surface-500"
					disabled={pageIndex === 0}
					onclick={() => (pageIndex = Math.max(0, pageIndex - 1))}
				>
					<i class="fa-solid fa-chevron-left mr-1"></i>{m.previous()}
				</button>
				<span class="text-sm text-surface-500">{pageIndex + 1} / {visiblePages.length}</span>
				<button
					type="button"
					class="btn preset-filled-primary-500"
					disabled={pageIndex >= visiblePages.length - 1}
					onclick={() => (pageIndex = Math.min(visiblePages.length - 1, pageIndex + 1))}
				>
					{m.next()}<i class="fa-solid fa-chevron-right ml-1"></i>
				</button>
			</div>
		{/if}
	{/if}
</div>
