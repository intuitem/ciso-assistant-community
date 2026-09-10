<script lang="ts">
	import { deserialize } from '$app/forms';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import Question from '$lib/components/Forms/Question.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// Trial answers live here and nowhere else — the preview stores nothing.
	let answers = $state<Record<string, any>>({});
	let view = $state<any>(data.initial);
	let busy = $state(false);

	const COLORS: Record<string, string> = {
		red: 'bg-red-100 text-red-800 ring-red-300 dark:bg-red-950 dark:text-red-200 dark:ring-red-800',
		orange:
			'bg-amber-100 text-amber-900 ring-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:ring-amber-800',
		green:
			'bg-emerald-100 text-emerald-800 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:ring-emerald-800',
		purple:
			'bg-violet-100 text-violet-800 ring-violet-300 dark:bg-violet-950 dark:text-violet-200 dark:ring-violet-800',
		blue: 'bg-sky-100 text-sky-800 ring-sky-300 dark:bg-sky-950 dark:text-sky-200 dark:ring-sky-800'
	};
	const NEUTRAL =
		'bg-surface-100 text-surface-700 ring-surface-300 dark:bg-surface-900 dark:text-surface-300 dark:ring-surface-700';

	const visiblePages = $derived((view?.pages ?? []).filter((p: any) => !p.hidden));
	// One page at a time, as the fill view presents it — pages exist to be walked
	// through, and a preview that stacks them tests a form nobody will ever see.
	let pageIndex = $state(0);
	// Answering can reveal or hide a page, so the index has to stay in range.
	const currentPage = $derived(
		visiblePages[Math.min(pageIndex, Math.max(0, visiblePages.length - 1))]
	);
	const hiddenPages = $derived((view?.pages ?? []).filter((p: any) => p.hidden));
	const rules = $derived((view?.outcomes_definition ?? []) as any[]);
	const fired = $derived((view?.computed_outcome ?? {}) as Record<string, any>);

	// Every change is re-evaluated by the same engine the live form uses, so the
	// preview cannot quietly disagree with what respondents will get.
	async function evaluate() {
		busy = true;
		try {
			const res = await fetch('?/evaluate', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ urn: data.quickFormUrn ?? null, answers })
			});
			const result: any = deserialize(await res.text());
			if (result.type === 'success' && result.data) view = result.data;
		} finally {
			busy = false;
		}
	}

	// The shared renderer hands back the whole answers map for its page.
	function onQuestionChange(_field: string, value: Record<string, unknown>) {
		answers = { ...answers, ...(value ?? {}) };
		evaluate();
	}

	function reset() {
		answers = {};
		pageIndex = 0;
		evaluate();
	}

	const label = (rule: any) => rule.label ?? rule.annotation ?? rule.ref_id;
</script>

<!-- The fill view is a centred max-w-4xl column with page padding; the form column
     here matches it exactly so the preview renders the form identically. The rail is
     an authoring aid and sits outside that width. -->
<div class="mx-auto max-w-6xl space-y-4 p-4">
	<div class="flex flex-wrap items-end justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-surface-900-100">{view?.name || m.preview()}</h1>
			<p class="text-sm text-surface-500">{m.lbQuickFormPreviewHint()}</p>
		</div>
		<div class="flex items-center gap-2">
			{#if busy}<span class="text-xs text-surface-400"
					><i class="fa-solid fa-spinner fa-spin"></i></span
				>{/if}
			<button type="button" class="btn btn-sm preset-tonal" onclick={reset}>
				<i class="fa-solid fa-rotate-left mr-1"></i>{m.lbQuickFormPreviewReset()}
			</button>
			<a
				class="btn btn-sm preset-tonal-primary"
				href={`/experimental/library-builder/${data.draftId}/quick-form?quick_form_urn=${encodeURIComponent(data.quickFormUrn)}`}
			>
				<i class="fa-solid fa-pen mr-1"></i>{m.lbBackToEditor()}
			</a>
		</div>
	</div>

	<div class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
		<div class="w-full max-w-4xl space-y-4">
			{#if view?.description}
				<div class="card bg-surface-50-950 shadow-sm p-4 text-sm">
					<MarkdownRenderer content={view.description} />
				</div>
			{/if}

			{#if visiblePages.length === 0}
				<div class="card bg-surface-50-950 shadow-sm p-6 text-center text-sm text-surface-500">
					{m.quickFormNoPages()}
				</div>
			{:else}
				<ol class="flex flex-wrap items-center gap-2 text-sm">
					{#each visiblePages as p, i (p.urn)}
						<li>
							<button
								type="button"
								class="rounded-full border px-3 py-1 transition-colors {i === pageIndex
									? 'border-primary-500 bg-primary-500 text-white'
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
						<section class="card bg-surface-50-950 shadow-sm space-y-4 p-4">
							<div>
								<h2 class="text-lg font-semibold">{currentPage.name}</h2>
								{#if currentPage.description}
									<MarkdownRenderer content={currentPage.description} class="mt-1 text-sm" />
								{/if}
							</div>
							<Question
								questions={currentPage.questions ?? {}}
								initialValue={answers}
								field="answers"
								onChange={onQuestionChange}
							/>
						</section>
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

			{#if hiddenPages.length}
				<section class="card border border-dashed border-surface-300-700 p-4">
					<h2 class="text-xs font-semibold uppercase tracking-wide text-surface-500">
						{m.lbQuickFormPreviewHidden()}
						<span class="text-surface-400">({hiddenPages.length})</span>
					</h2>
					<div class="mt-2 flex flex-wrap gap-2">
						{#each hiddenPages as p (p.urn)}
							<span class="rounded-lg bg-surface-100-900 px-2.5 py-1 text-xs text-surface-500"
								>{p.name}</span
							>
						{/each}
					</div>
				</section>
			{/if}
		</div>

		<aside class="space-y-4 lg:sticky lg:top-4 lg:self-start">
			<div class="card bg-surface-50-950 shadow-sm p-4 text-xs">
				<div class="flex justify-between text-surface-500">
					<span>{m.quickFormAnswered()}</span>
					<span class="font-mono"
						>{view?.progress?.answered_count ?? 0}/{view?.progress?.total_count ?? 0}</span
					>
				</div>
				<div class="mt-2 flex justify-between text-surface-500">
					<span>{m.score()}</span>
					<span class="font-mono">{view?.score ?? '—'}</span>
				</div>
				<div class="mt-2 flex justify-between text-surface-500">
					<span>{m.lbQuickFormPreviewComplete()}</span>
					<span class="font-mono">{view?.progress?.complete ? '✓' : '—'}</span>
				</div>
			</div>

			{#if rules.length}
				<div class="card bg-surface-50-950 shadow-sm p-4">
					<h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-surface-500">
						{m.computedOutcomes()}
					</h3>
					<div class="space-y-2">
						{#each rules as rule (rule.ref_id)}
							{@const on = rule.ref_id in fired}
							<div class="flex items-start gap-2 {on ? '' : 'opacity-45'}">
								<i
									class="fa-solid {on
										? 'fa-circle-check text-emerald-500'
										: 'fa-circle text-surface-300'} mt-0.5 text-xs"
								></i>
								<span
									class="rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset {COLORS[
										rule.color ?? ''
									] ?? NEUTRAL}">{label(rule)}</span
								>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</aside>
	</div>
</div>
