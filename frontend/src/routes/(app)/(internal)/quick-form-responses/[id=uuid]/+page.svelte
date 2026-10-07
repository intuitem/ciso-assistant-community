<script lang="ts">
	import { ruleLabel } from '$lib/components/QuickForms/rule-label';
	import { deserialize } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import Question from '$lib/components/Forms/Question.svelte';
	import ProjectionCard from '$lib/components/QuickForms/ProjectionCard.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { isDark } from '$lib/utils/helpers';
	import { m } from '$paraglide/messages';
	import { canPerformActionOnObject } from '$lib/utils/access-control';
	import { urlModelForDjangoName, localNameForDjangoName } from '$lib/utils/crud';
	import type { PageData } from './$types';

	// Referenceable models (core/object_references.py REFERENCEABLE) to their routes.
	const SUBJECT_ROUTES: Record<string, string> = {
		applied_control: 'applied-controls',
		asset: 'assets',
		risk_scenario: 'risk-scenarios',
		vulnerability: 'vulnerabilities',
		perimeter: 'perimeters',
		entity: 'entities'
	};

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
	// Not what the request points at — what it caused to exist.
	const producedObjects = $derived(
		((content.produced_objects ?? []) as any[]).map((entry) => ({
			...entry,
			label: localNameForDjangoName(entry.model) ?? entry.model,
			href: urlModelForDjangoName(entry.model)
				? `/${urlModelForDjangoName(entry.model)}/${entry.id}`
				: null
		}))
	);
	// The server decides; offering a button it will refuse is worse than hiding it.
	const canReview = $derived(!!content.can_review);
	const suggestedActions = $derived((data.suggestedActions ?? []) as any[]);
	const acceptPreview = $derived((data.acceptPreview ?? []) as any[]);

	// Override at accept, per target. Only the tier target offers it for now.
	const OVERRIDABLE = new Set(['entity.tier']);
	let overrides: Record<string, { tier: string; note: string }> = $state({});
	let overrideTiers: { id: string; name: string }[] = $state([]);

	async function toggleOverride(target: string) {
		if (overrides[target]) {
			const { [target]: _, ...rest } = overrides;
			overrides = rest;
			return;
		}
		if (!overrideTiers.length) {
			let tiers: unknown = null;
			try {
				const res = await fetch('/tiers?is_visible=true');
				const body = res.ok ? await res.json().catch(() => null) : null;
				tiers = body?.results ?? body;
			} catch {
				tiers = null;
			}
			if (!Array.isArray(tiers) || !tiers.length) {
				toastStore.trigger({
					message: m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			overrideTiers = tiers;
		}
		overrides = { ...overrides, [target]: { tier: '', note: '' } };
	}

	const activeOverrides = $derived(
		Object.fromEntries(Object.entries(overrides).filter(([, o]) => o.tier))
	);

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
	const canEditAnswers = $derived(!!content.can_edit_answers);

	let busy = $state(false);
	let reopenObservation = $state('');

	// The backend status travels in the action payload, not the HTTP response.
	function actionError(result: any): string | null {
		const data = result?.type === 'success' || result?.type === 'failure' ? result.data : null;
		const status = data?.status;
		if (typeof status !== 'number' || status < 400) return null;
		const code = data?.body?.error ?? data?.body?.detail;
		if (typeof code !== 'string') return safeTranslate('anErrorOccurred');
		// A refused override says why (e.g. a missing justification).
		const reason = data?.body?.reason;
		return typeof reason === 'string'
			? `${safeTranslate(code)}: ${safeTranslate(reason)}`
			: safeTranslate(code);
	}

	async function post(action: string, body: Record<string, unknown>) {
		busy = true;
		try {
			const res = await fetch(`?/${action}`, {
				method: 'POST',
				body: JSON.stringify({ id: response.id, ...body })
			});
			const result: any = deserialize(await res.text());
			const failure = actionError(result);
			if (!res.ok || failure) {
				toastStore.trigger({
					message: failure ?? safeTranslate('anErrorOccurred'),
					background: 'preset-filled-error-500'
				});
			}
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	// One write at a time per question. Controls stay enabled while a save is in
	// flight, so two edits can overlap and the older reply would land last.
	const saveChain: Record<string, Promise<unknown>> = {};

	async function saveAnswer(urn: string, value: unknown) {
		const previous = saveChain[urn] ?? Promise.resolve();
		const next = previous
			.catch(() => {})
			.then(() => post('updateAnswers', { answers: { [urn]: value } }));
		saveChain[urn] = next;
		return next;
	}

	// Files go through the multipart action, not the JSON answers patch.
	async function uploadAttachment(urn: string, file: File) {
		const body = new FormData();
		body.append('id', response.id);
		body.append('question', urn);
		body.append('file', file);
		const res = await fetch('?/uploadAttachment', { method: 'POST', body });
		const result: any = deserialize(await res.text());
		const failure = actionError(result);
		if (failure) throw new Error(failure);
		await invalidateAll();
	}

	async function removeAttachment(_urn: string, attachmentId: string) {
		await post('removeAttachment', { attachmentId });
	}

	async function searchReferences(urn: string, search: string) {
		const query = new URLSearchParams({ question: urn, search });
		const res = await fetch(`/quick-form-responses/${response.id}/reference-options?${query}`);
		if (!res.ok) return [];
		return (await res.json()).results ?? [];
	}

	const statusColor: Record<string, string> = {
		draft: 'preset-tonal',
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
						{content.quick_form?.name ?? response.quick_form?.str}
					</a>
					· {response.folder?.str}
				</p>
			</div>
			<span class="badge {statusColor[response.status] ?? 'preset-tonal'}">
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
			<!-- Collapsed by default: the list shrinks with every answer, and an open
			     list above the questions would move them under the cursor. -->
			<details
				class="group rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40"
				data-testid="missing-required"
			>
				<summary
					class="flex cursor-pointer list-none items-center gap-1.5 font-medium text-amber-900 dark:text-amber-200"
				>
					<i class="fa-solid fa-circle-exclamation"></i>
					{m.quickFormMissingRequired({ count: missingRequired.length })}
					<i
						class="fa-solid fa-chevron-down ml-auto text-xs transition-transform group-open:rotate-180"
						aria-hidden="true"
					></i>
				</summary>
				<ul class="mt-2 list-inside list-disc text-xs text-amber-800 dark:text-amber-300">
					{#each missingRequired as q (q.urn)}
						<li>
							{q.text}{#if q.page}<span class="text-amber-600 dark:text-amber-400">
									&nbsp;— {q.page}</span
								>{/if}
						</li>
					{/each}
				</ul>
			</details>
		{/if}

		{#if canEditAnswers}
			<p class="text-xs text-surface-500">
				<i class="fa-solid fa-cloud-arrow-up mr-1"></i>
				{response.ref_id
					? m.quickFormDraftSavedWithRef({ ref: response.ref_id })
					: m.quickFormDraftSaved()}
			</p>
		{/if}

		{#if content.subject}
			{@const href = SUBJECT_ROUTES[content.subject.model ?? '']}
			<p class="text-sm" data-testid="response-subject">
				<span class="text-xs font-semibold uppercase tracking-wider text-surface-500"
					>{m.responseSubject()}</span
				>
				{#if content.subject.str && href}
					<a class="anchor ml-1" href={`/${href}/${content.subject.id}`}>{content.subject.str}</a>
				{:else}
					<span class="ml-1">{content.subject.str ?? m.objectsNotVisible({ count: 1 })}</span>
				{/if}
			</p>
		{/if}

		{#if content.computed_outcome && Object.keys(content.computed_outcome).length > 0}
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-xs font-semibold uppercase tracking-wider text-surface-500"
					>{m.computedOutcomes()}</span
				>
				{#each Object.entries(content.computed_outcome) as [refId, payload]}
					{@const color = (payload as any)?.color}
					<span
						class="badge preset-tonal"
						style={color ? `background:${color};color:${isDark(color) ? 'white' : 'black'}` : ''}
					>
						{ruleLabel(payload as any, refId)}
					</span>
				{/each}
			</div>
		{/if}

		{#if content.computed_values && Object.keys(content.computed_values).length > 0 && content.scored_complete !== false}
			{@const rules = (content.quick_form?.outcomes_definition ?? []) as any[]}
			<div class="flex flex-wrap items-center gap-3" data-testid="computed-values">
				<span class="text-xs font-semibold uppercase tracking-wider text-surface-500"
					>{m.computedValues()}</span
				>
				{#each Object.entries(content.computed_values) as [refId, value]}
					{@const rule = rules.find((r) => r.ref_id === refId)}
					<span class="text-sm">
						<span class="text-surface-600-400">{ruleLabel(rule, refId)}</span>
						<span class="font-mono font-semibold ml-1"
							>{Number.isInteger(value) ? value : (value as number).toFixed(2)}</span
						>
					</span>
				{/each}
			</div>
		{/if}

		{#if content.projection?.length && !content.applications?.length}
			<ProjectionCard
				rows={content.projection}
				rules={content.quick_form?.outcomes_definition ?? []}
				nested
			/>
		{/if}

		{#if content.applications?.length}
			<div
				class="rounded-lg border border-success-300 bg-success-50 dark:bg-success-500/10 p-3"
				data-testid="applied-on-accept"
			>
				<p
					class="text-xs font-semibold uppercase tracking-wider text-success-700 dark:text-success-400"
				>
					<i class="fa-solid fa-circle-check mr-1"></i>{response.decided_by &&
					response.decided_by === response.submitted_by
						? m.appliedOnSubmit()
						: m.appliedOnAccept()}
				</p>
				<ul class="mt-2 flex flex-col gap-1 text-sm">
					{#each content.applications as application (application.target)}
						<li class="flex flex-wrap items-baseline gap-2">
							<span class="font-medium">{safeTranslate(application.label)}</span>
							<span class="font-mono"
								>{safeTranslate(application.previous || '—')} → {safeTranslate(
									application.new
								)}</span
							>
							{#if application.overridden}
								<span class="badge preset-tonal-warning text-xs">{m.override()}</span>
							{/if}
							{#if application.note}
								<span class="text-surface-500">{application.note}</span>
							{/if}
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if producedObjects.length}
			<div class="rounded-lg border border-success-300 bg-success-50 dark:bg-success-500/10 p-3">
				<p
					class="text-xs font-semibold uppercase tracking-wider text-success-700 dark:text-success-400"
				>
					<i class="fa-solid fa-circle-check mr-1"></i>{m.producedObjects()}
				</p>
				<ul class="mt-2 flex flex-col gap-1 text-sm">
					{#each producedObjects as obj (obj.id)}
						<li class="flex flex-wrap items-baseline gap-2">
							{#if obj.href}
								<a class="anchor font-medium" href={obj.href}>{obj.ref_id || obj.name}</a>
							{:else}
								<span class="font-medium">{obj.ref_id || obj.name}</span>
							{/if}
							<span class="text-surface-500">{safeTranslate(obj.label)}</span>
							{#if obj.ref_id && obj.name}
								<span class="text-surface-500">— {obj.name}</span>
							{/if}
						</li>
					{/each}
				</ul>
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

		<!-- The asking side. `can_edit_answers` is already requester-gated server-side. -->
		{#if viewerIsRequester || content.can_edit_answers}
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
					<!-- Only once Submit can be clicked: before that it describes nothing. -->
					{#if content.on_submit && content.progress?.complete}
						<span class="text-xs text-surface-500" data-testid="on-submit-hint">
							<i class="fa-solid {content.on_submit === 'apply' ? 'fa-bolt' : 'fa-user-check'} mr-1"
							></i>{content.on_submit === 'apply' ? m.onSubmitApplies() : m.onSubmitGoesToReview()}
						</span>
					{/if}
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
				<!-- To re-run a sent or decided response, not the draft being filled. -->
				{#if response.status !== 'draft'}
					<button
						type="button"
						class="btn btn-sm preset-tonal"
						disabled={busy}
						onclick={() => post('clone', {})}
					>
						<i class="fa-solid fa-copy mr-1"></i>{m.quickFormClone()}
					</button>
				{/if}
			</div>
		{/if}
		<!-- Independent of the block above: being the requester and being able to decide
		     are not exclusive. With self-validation on the same person is both, and an
		     {:else if} silently dropped one of the two sets. Deciding keys on `approve`,
		     not `change` — the Approver role holds one and not the other. -->
		{#if canReview}
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
			{#if (response.status === 'submitted' || response.status === 'in_review') && acceptPreview.length}
				<div
					class="rounded-lg border border-surface-200-800 bg-surface-100-900 p-3 text-sm"
					data-testid="accept-preview"
				>
					<p class="text-xs font-semibold uppercase tracking-wider text-surface-500">
						{m.onAcceptPreview()}
					</p>
					<ul class="mt-2 flex flex-col gap-1">
						{#each acceptPreview as row (row.target)}
							<li class="flex flex-wrap items-baseline gap-2">
								<span class="font-medium">{safeTranslate(row.label)}</span>
								{#if row.subject}<span class="text-surface-500">· {row.subject}</span>{/if}
								{#if row.ok}
									<span class="font-mono"
										>{safeTranslate(row.current || '—')} → {safeTranslate(row.proposed)}</span
									>
								{:else}
									<span class="text-warning-700 dark:text-warning-400">
										<i class="fa-solid fa-triangle-exclamation mr-1"></i>{safeTranslate(row.reason)}
									</span>
								{/if}
								{#if OVERRIDABLE.has(row.target) && (row.ok || row.reason === 'noTierResolved')}
									<button
										type="button"
										class="text-xs anchor"
										onclick={() => toggleOverride(row.target)}
										data-testid="override-toggle"
									>
										{overrides[row.target] ? m.cancel() : m.overrideAtAccept()}
									</button>
								{/if}
								{#if overrides[row.target]}
									<div class="flex w-full flex-wrap items-center gap-2" data-testid="override-form">
										<select class="select w-40 text-sm" bind:value={overrides[row.target].tier}>
											<option value="">--</option>
											{#each overrideTiers as tier (tier.id)}
												<option value={tier.id}>{safeTranslate(tier.name)}</option>
											{/each}
										</select>
										<input
											class="input flex-1 min-w-48 text-sm"
											placeholder={m.overrideJustification()}
											bind:value={overrides[row.target].note}
										/>
									</div>
								{/if}
							</li>
						{/each}
					</ul>
				</div>
			{/if}
			<!-- The reviewer. Claiming is optional; a decision always carries a resolution. -->
			<div class="flex flex-wrap items-center gap-2 pt-1">
				{#if response.status === 'draft' && !canEditAnswers}
					<!-- Not to the requester themselves: an analyst assessing in-house is both. -->
					<span class="text-sm text-surface-500">
						<i class="fa-solid fa-hourglass-half mr-1"></i>{m.quickFormAwaitingRequester()}
					</span>
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
						autocomplete="off"
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
								observation: reopenObservation || null,
								...(Object.keys(activeOverrides).length ? { overrides: activeOverrides } : {})
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
						attachments={content.attachments ?? {}}
						references={content.references ?? {}}
						onSearchReferences={canEditAnswers ? searchReferences : undefined}
						attachmentHref={(a) => `/quick-form-responses/${response.id}/attachments/${a.id}`}
						onUpload={canEditAnswers ? uploadAttachment : undefined}
						onRemoveAttachment={canEditAnswers ? removeAttachment : undefined}
						questions={currentPage.questions ?? {}}
						initialValue={content.answers ?? {}}
						field="answers"
						disabled={!canEditAnswers}
						lockedUrns={response.subject_locked && content.quick_form?.subject_question_urn
							? [content.quick_form.subject_question_urn]
							: []}
						onChange={saveAnswer}
					/>
				</div>
			{/key}

			{#if visiblePages.length > 1}
				<div class="flex items-center justify-between">
					<button
						type="button"
						class="btn preset-outlined-surface-500 enabled:hover:bg-surface-200-800"
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
	{/if}
</div>
