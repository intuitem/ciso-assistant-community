<script lang="ts">
	import { invalidateAll, goto } from '$app/navigation';
	import { deserialize } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getModalStore } from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const STATUS: Record<string, { label: string; dot: string }> = {
		draft: { label: m.quickFormDraftStatus(), dot: 'bg-sky-500' },
		submitted: { label: m.quickFormAwaitingReview(), dot: 'bg-amber-500' },
		in_review: { label: m.quickFormInReviewStatus(), dot: 'bg-violet-500' },
		closed: { label: m.quickFormClosedStatus(), dot: 'bg-surface-400' }
	};

	const RESOLUTION: Record<string, string> = {
		accepted: m.quickFormAccepted(),
		rejected: m.quickFormRejected(),
		dropped: m.quickFormDropped(),
		auto: m.quickFormAutoClosed()
	};

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

	const requests = $derived((data.requests ?? []) as any[]);
	const drafts = $derived(requests.filter((r) => r.status === 'draft'));
	const rest = $derived(requests.filter((r) => r.status !== 'draft'));
	const portals = $derived((data.portals ?? []) as { id: string; name: string }[]);

	const outcomes = (r: any) =>
		Object.entries(r.computed_outcome ?? {}).map(([ref_id, v]: [string, any]) => ({
			ref_id,
			label: v?.label ?? v?.annotation ?? ref_id,
			color: v?.color
		}));
	const fmt = (d: string | null) =>
		d ? new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '—';

	const modalStore = getModalStore();
	let busy = $state('');

	async function act(id: string, action: 'drop' | 'clone' | 'remove') {
		if (busy) return;
		busy = id;
		try {
			const body = new FormData();
			body.append('id', id);
			const res = await fetch(`?/${action}`, { method: 'POST', body });
			const result: any = deserialize(await res.text());
			if (result.type === 'success' && result.data?.redirect) {
				await goto(result.data.redirect);
				return;
			}
			await invalidateAll();
		} finally {
			busy = '';
		}
	}

	// Drop and delete are irreversible from the requester's side, so both confirm.
	function confirmAct(id: string, action: 'drop' | 'remove', name: string) {
		modalStore.trigger({
			type: 'confirm',
			title: action === 'drop' ? m.quickFormDropTitle() : m.delete(),
			body: action === 'drop' ? m.quickFormDropBody({ name }) : m.deleteModalMessage({ name }),
			buttonTextConfirm: action === 'drop' ? m.quickFormDrop() : m.delete(),
			response: (confirmed: boolean) => {
				if (confirmed) act(id, action);
			}
		});
	}
</script>

{#snippet askFrom()}
	{#if portals.length}
		<span>
			{m.myRequestsAskFrom()}
			{#each portals as portal, i (portal.id)}<a
					href={`/portal/${portal.id}`}
					class="font-medium text-violet-600 hover:underline">{portal.name}</a
				>{i < portals.length - 1 ? ', ' : ''}{/each}
		</span>
	{/if}
{/snippet}

<div class="mb-6 flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="text-2xl font-bold text-surface-900-100">{m.myRequests()}</h1>
		<p class="text-sm text-surface-500">{m.myRequestsSubtitle()}</p>
	</div>
	<p class="text-sm text-surface-500">{@render askFrom()}</p>
</div>

{#snippet requestRow(r: any)}
	<a
		href={`/quick-form-responses/${r.id}`}
		class="flex items-center gap-4 p-4 transition-colors hover:bg-surface-100-900"
	>
		<span class="h-2 w-2 shrink-0 rounded-full {STATUS[r.status]?.dot}"></span>
		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap items-center gap-2">
				{#if r.ref_id}
					<span class="shrink-0 font-mono text-[11px] text-surface-400">{r.ref_id}</span>
				{/if}
				<span class="truncate font-semibold text-surface-900-100">{r.name}</span>
				<span class="text-[11px] text-surface-400">{r.quick_form}</span>
				{#if r.resolution}
					<span
						class="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide {r.resolution ===
						'accepted'
							? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
							: r.resolution === 'rejected'
								? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
								: 'bg-surface-200-800 text-surface-500'}">{RESOLUTION[r.resolution]}</span
					>
				{/if}
				{#if r.cloned_from}
					<span class="text-[10px] text-surface-400"
						><i class="fa-solid fa-copy mr-0.5"></i>{r.cloned_from}</span
					>
				{/if}
			</div>
			{#if outcomes(r).length}
				<div class="mt-1.5 flex flex-wrap gap-1">
					{#each outcomes(r) as o (o.ref_id)}
						<span
							class="rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset {COLORS[
								o.color ?? ''
							] ?? NEUTRAL}">{o.label}</span
						>
					{/each}
				</div>
			{/if}
		</div>
		<div class="shrink-0 text-right text-xs">
			{#if r.status === 'draft'}
				<span class="text-sky-600"
					>{r.progress.answered_count}/{r.progress.total_count}
					{m.quickFormAnswered()}</span
				>
			{:else}
				<span class="text-surface-500">{STATUS[r.status]?.label}</span>
			{/if}
			<div class="text-surface-400">{fmt(r.submitted_at ?? r.updated_at)}</div>
		</div>
	</a>
	<div class="flex shrink-0 items-center gap-1 pr-4">
		{#if r.status === 'draft'}
			<button
				type="button"
				disabled={!!busy}
				onclick={() => confirmAct(r.id, 'remove', r.name)}
				class="rounded-md px-2 py-1 text-xs text-surface-500 hover:bg-surface-200-800 hover:text-red-600"
				title={m.delete()}><i class="fa-solid fa-trash"></i></button
			>
		{:else if r.status === 'submitted' || r.status === 'in_review'}
			<button
				type="button"
				disabled={!!busy}
				onclick={() => confirmAct(r.id, 'drop', r.name)}
				class="rounded-md px-2 py-1 text-xs text-surface-500 hover:bg-surface-200-800 hover:text-amber-600"
				title={m.quickFormDrop()}><i class="fa-solid fa-ban"></i></button
			>
		{/if}
		<button
			type="button"
			disabled={!!busy}
			onclick={() => act(r.id, 'clone')}
			class="rounded-md px-2 py-1 text-xs text-surface-500 hover:bg-surface-200-800 hover:text-violet-600"
			title={m.quickFormClone()}><i class="fa-solid fa-copy"></i></button
		>
	</div>
{/snippet}

{#if drafts.length}
	<section class="mb-8">
		<h2 class="mb-3 text-xs font-semibold uppercase tracking-wide text-surface-500">
			{m.quickFormUnfinished()} <span class="text-surface-400">({drafts.length})</span>
		</h2>
		<p class="mb-3 text-xs text-surface-500">{m.quickFormUnfinishedHint()}</p>
		<div
			class="divide-y divide-surface-200-800 overflow-hidden rounded-xl border border-sky-200 bg-surface-50-950 dark:border-sky-900"
		>
			{#each drafts as r (r.id)}<div class="flex items-center">{@render requestRow(r)}</div>{/each}
		</div>
	</section>
{/if}

<section>
	<h2 class="mb-3 text-xs font-semibold uppercase tracking-wide text-surface-500">
		{m.quickFormFiled()} <span class="text-surface-400">({rest.length})</span>
	</h2>
	{#if rest.length}
		<div
			class="divide-y divide-surface-200-800 overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950"
		>
			{#each rest as r (r.id)}<div class="flex items-center">{@render requestRow(r)}</div>{/each}
		</div>
	{:else}
		<div
			class="rounded-xl border border-dashed border-surface-300-700 p-8 text-center text-sm text-surface-400"
		>
			<i class="fa-solid fa-inbox mb-2 block text-2xl text-surface-300"></i>
			{m.quickFormNoRequests()}
			<div class="mt-1">{@render askFrom()}</div>
		</div>
	{/if}
</section>
