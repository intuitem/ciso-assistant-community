<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import MarkdownRenderer from '#lib/components/MarkdownRenderer.svelte';
	import {
		daysFrom,
		relative,
		userName,
		type Evidence,
		type RequirementDetail,
		type Revision,
		type ReviewStatus
	} from './types';

	interface Props {
		evidence: Evidence;
		revisions: Revision[] | undefined;
		requirements: RequirementDetail[] | undefined;
		viewedId: string | undefined;
		me: string | undefined;
		fourEyes: boolean;
		busy: boolean;
		error: string;
		rejecting: boolean;
		onView: (id: string) => void;
		onDecide: (decision: Exclude<ReviewStatus, 'pending'>, comment: string) => void;
	}

	let {
		evidence,
		revisions,
		requirements,
		viewedId,
		me,
		fourEyes,
		busy,
		error,
		rejecting = $bindable(),
		onView,
		onDecide
	}: Props = $props();

	const REASONS = [
		m.reviewReasonOutOfDate(),
		m.reviewReasonWrongScope(),
		m.reviewReasonIncomplete(),
		m.reviewReasonIllegible(),
		m.reviewReasonWrongDocument()
	];
	const SHOWN_REQUIREMENTS = 5;

	let comment = $state('');
	let changing = $state(false);
	let commentEl: HTMLTextAreaElement | undefined = $state();

	$effect(() => {
		evidence.id;
		comment = '';
		changing = false;
	});
	$effect(() => {
		if (rejecting) commentEl?.focus();
	});

	const latest = $derived(revisions?.[0]);
	const decided = $derived(latest && latest.review_status !== 'pending' && !changing);
	const blocked = $derived(fourEyes && !!me && latest?.uploaded_by?.id === me);
	const expiry = $derived(evidence.expiry_date ? daysFrom(evidence.expiry_date) : null);

	// The fastest review is the one already done: same bytes as a version someone approved.
	const hint = $derived.by(() => {
		if (!latest || !revisions || revisions.length < 2) return undefined;
		const twin = revisions
			.slice(1)
			.find((r) => latest.attachment_hash && r.attachment_hash === latest.attachment_hash);
		if (twin?.review_status === 'approved')
			return {
				tone: 'success',
				text: twin.reviewed_by
					? m.reviewSameFileApprovedBy({
							version: twin.version,
							name: userName(twin.reviewed_by)
						})
					: m.reviewSameFileApproved({ version: twin.version })
			};
		if (twin) return { tone: 'neutral', text: m.reviewSameFile({ version: twin.version }) };
		return { tone: 'warning', text: m.reviewChangedSince({ version: revisions[1].version }) };
	});

	function addReason(r: string) {
		comment = comment.trim() ? `${comment.trim()} ${r}.` : `${r}.`;
		commentEl?.focus();
	}

	function reject() {
		if (comment.trim()) onDecide('rejected', comment);
	}

	const HINT: Record<string, { icon: string; style: string }> = {
		success: { icon: 'fa-clone', style: 'border-success-500 text-success-700-300' },
		warning: { icon: 'fa-pen-to-square', style: 'border-warning-500 text-warning-700-300' },
		neutral: { icon: 'fa-clone', style: 'border-surface-400-600 text-surface-700-300' }
	};

	const STATUS: Record<ReviewStatus, { icon: string; tone: string; label: string }> = {
		approved: {
			icon: 'fa-circle-check',
			tone: 'text-success-600-400',
			label: m.reviewStatusApproved()
		},
		rejected: {
			icon: 'fa-circle-xmark',
			tone: 'text-error-600-400',
			label: m.reviewStatusRejected()
		},
		pending: { icon: 'fa-circle-dot', tone: 'text-warning-600-400', label: m.reviewToReview() }
	};
</script>

<div class="flex flex-col text-sm divide-y divide-surface-200-800 [&>*]:p-4">
	<section class="space-y-3" aria-label={m.reviewDecision()}>
		{#if !latest}
			<p class="text-surface-600-400">{m.loading()}…</p>
		{:else if decided}
			{@const s = STATUS[latest.review_status]}
			<div class="flex items-start gap-3">
				<i class="fa-solid {s.icon} {s.tone} text-2xl mt-0.5"></i>
				<div class="min-w-0 grow">
					<p class="font-semibold">{s.label} · v{latest.version}</p>
					{#if latest.reviewed_by || latest.reviewed_at}
						<p class="text-xs text-surface-600-400">
							{[
								latest.reviewed_by && userName(latest.reviewed_by),
								latest.reviewed_at && relative(latest.reviewed_at)
							]
								.filter(Boolean)
								.join(' · ')}
						</p>
					{/if}
					{#if latest.review_comment}
						<p class="mt-2 text-surface-800-200">“{latest.review_comment}”</p>
					{/if}
				</div>
			</div>
			<button class="btn btn-sm preset-tonal w-full" onclick={() => (changing = true)}
				>{m.reviewChangeDecision()}</button
			>
		{:else}
			<div class="flex items-center justify-between text-xs text-surface-600-400">
				<span
					>v{latest.version}{latest.uploaded_by ? ` · ${userName(latest.uploaded_by)}` : ''}</span
				>
				<span>{relative(latest.created_at)}</span>
			</div>
			{#if hint}
				{@const h = HINT[hint.tone]}
				<p class="flex items-center gap-2 border-l-2 pl-3 py-1 text-xs font-medium {h.style}">
					<i class="fa-solid fa-fw {h.icon}"></i>{hint.text}
				</p>
			{/if}
			{#if blocked}
				<p class="rounded-lg px-3 py-2 text-xs bg-surface-100-900">
					<i class="fa-solid fa-user-lock mr-1"></i>{m.reviewFourEyesBlocked()}
				</p>
			{:else if rejecting}
				<div class="space-y-2">
					<label for="review-comment" class="text-xs font-semibold">{m.reviewRejectWhy()}</label>
					<textarea
						id="review-comment"
						bind:this={commentEl}
						bind:value={comment}
						class="textarea text-sm"
						rows="3"
						placeholder={m.reviewRejectPlaceholder()}
						onkeydown={(e) => {
							if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
								e.preventDefault();
								reject();
							}
							if (e.key === 'Escape') rejecting = false;
						}}
					></textarea>
					<div class="flex flex-wrap gap-1">
						{#each REASONS as r (r)}
							<button
								type="button"
								class="chip preset-outlined-surface-500 text-xs"
								onclick={() => addReason(r)}>{r}</button
							>
						{/each}
					</div>
					<div class="flex gap-2">
						<button
							class="btn preset-filled-error-500 grow"
							disabled={busy || !comment.trim()}
							onclick={reject}>{m.reject()} <kbd class="kbd text-[10px] ml-1">⌘↵</kbd></button
						>
						<button class="btn preset-tonal" onclick={() => (rejecting = false)}
							>{m.cancel()}</button
						>
					</div>
				</div>
			{:else}
				<div class="grid grid-cols-2 gap-2">
					<button
						class="btn bg-success-600 text-white hover:bg-success-700"
						disabled={busy}
						onclick={() => onDecide('approved', '')}
						><i class="fa-solid fa-check"></i>{m.approve()}<kbd class="kbd text-[10px]">A</kbd
						></button
					>
					<button
						class="btn preset-outlined-error-500"
						disabled={busy}
						onclick={() => (rejecting = true)}
						><i class="fa-solid fa-xmark"></i>{m.reject()}<kbd class="kbd text-[10px]">R</kbd
						></button
					>
				</div>
			{/if}
			{#if changing}
				<button class="text-xs anchor" onclick={() => (changing = false)}
					>{m.reviewKeepDecision()}</button
				>
			{/if}
		{/if}
		{#if error}
			<p class="text-xs text-error-600-400" role="alert">{error}</p>
		{/if}
	</section>

	{#if expiry !== null && expiry < 30}
		<p
			class="flex items-center gap-2 text-xs {expiry < 0
				? 'text-error-600-400'
				: 'text-warning-700-300'}"
		>
			<i class="fa-regular fa-hourglass-half"></i>
			{expiry < 0
				? m.reviewExpiredDaysAgo({ days: -expiry })
				: m.reviewExpiresInDays({ days: expiry })}
		</p>
	{/if}

	<section class="space-y-2">
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400">
			{m.reviewRequirementsCount({ count: evidence.requirement_assessments.length })}
		</h3>
		{#if evidence.requirement_assessments.length === 0}
			<p class="text-xs text-surface-600-400">{m.reviewNotLinked()}</p>
		{:else if !requirements}
			<p class="text-xs text-surface-600-400">{m.loading()}…</p>
		{:else}
			<ul class="space-y-1">
				{#each requirements.slice(0, SHOWN_REQUIREMENTS) as ra (ra.id)}
					<li>
						<details class="group rounded-lg hover:bg-surface-100-900 open:bg-surface-100-900">
							<summary class="cursor-pointer list-none px-2 py-1.5 flex gap-2 items-baseline">
								<i
									class="fa-solid fa-chevron-right text-[10px] text-surface-500 transition-transform group-open:rotate-90"
								></i>
								<span class="min-w-0">
									<span class="block truncate">{ra.name}</span>
									<span class="block text-xs text-surface-600-400 truncate"
										>{ra.compliance_assessment.str}</span
									>
								</span>
							</summary>
							<div class="px-2 pb-2 pl-6 space-y-2 text-xs">
								{#if ra.requirement?.typical_evidence}
									<div class="rounded-lg bg-primary-50-950 p-2">
										<p class="font-semibold mb-1">{m.typicalEvidence()}</p>
										<MarkdownRenderer content={ra.requirement.typical_evidence} />
									</div>
								{:else if ra.description}
									<MarkdownRenderer content={ra.description} />
								{/if}
								<a class="anchor" href="/requirement-assessments/{ra.id}/edit"
									>{m.reviewOpenRequirement()}</a
								>
							</div>
						</details>
					</li>
				{/each}
			</ul>
			{#if evidence.requirement_assessments.length > SHOWN_REQUIREMENTS}
				<a class="text-xs anchor" href="/evidences/{evidence.id}"
					>{m.reviewMore({
						count: evidence.requirement_assessments.length - SHOWN_REQUIREMENTS
					})}</a
				>
			{/if}
		{/if}
	</section>

	<section class="space-y-2">
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400">
			{m.reviewHistory()}
		</h3>
		{#if !revisions}
			<p class="text-xs text-surface-600-400">{m.loading()}…</p>
		{:else}
			<ol class="space-y-0.5">
				{#each revisions as rev (rev.id)}
					{@const s = STATUS[rev.review_status]}
					<li>
						<button
							class="w-full text-left rounded-lg px-2 py-1.5 flex gap-2 items-center text-xs {viewedId ===
							rev.id
								? 'bg-primary-100-900'
								: 'hover:bg-surface-100-900'}"
							onclick={() => onView(rev.id)}
							title={rev.review_comment || s.label}
						>
							<i class="fa-solid fa-fw shrink-0 {s.icon} {s.tone}" aria-label={s.label}></i>
							<span class="font-mono font-semibold">v{rev.version}</span>
							<span class="min-w-0 truncate grow">{rev.attachment ?? rev.link ?? '—'}</span>
							<span class="text-surface-600-400 shrink-0">{relative(rev.created_at)}</span>
						</button>
					</li>
				{/each}
			</ol>
		{/if}
	</section>
</div>
