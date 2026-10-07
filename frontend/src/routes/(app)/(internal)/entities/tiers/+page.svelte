<script lang="ts">
	import { deserialize } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import TierBadge from '$lib/components/ModelTable/field/TierBadge.svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { canPerformAction } from '$lib/utils/access-control';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Tier {
		id: string;
		name: string;
		description?: string;
		rank: number;
		hexcolor: string;
		is_visible: boolean;
		builtin: boolean;
		entities_count: number;
		solutions_count?: number;
		in_history?: boolean;
	}

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const toastStore = getToastStore();

	let tiers: Tier[] = $state([]);
	$effect(() => {
		tiers = [...(data.tiers as Tier[])];
	});

	const rootFolderId = $derived(page.data.user?.root_folder_id);
	const canEdit = $derived(
		canPerformAction({
			user: page.data.user,
			action: 'change',
			model: 'tier',
			domain: rootFolderId
		})
	);
	const canAdd = $derived(
		canPerformAction({ user: page.data.user, action: 'add', model: 'tier', domain: rootFolderId })
	);
	const canDelete = $derived(
		canPerformAction({
			user: page.data.user,
			action: 'delete',
			model: 'tier',
			domain: rootFolderId
		})
	);

	let busy = $state(false);
	let newName = $state('');
	let newColor = $state('#64748b');
	let dragIndex: number | null = $state(null);

	// Colours come from the database and reach inline styles: only bare hex gets through.
	const HEX = /^#[0-9a-fA-F]{3,8}$/;
	const FALLBACK = '#94a3b8';
	const colorOf = (tier: Tier) => (HEX.test(tier.hexcolor ?? '') ? tier.hexcolor : FALLBACK);
	const labelOf = (tier: Tier) => (tier.builtin ? safeTranslate(tier.name) : tier.name);

	// The rail is the scale itself: the visible tiers' colours, most critical first.
	const railGradient = $derived.by(() => {
		const colors = tiers.filter((t) => t.is_visible).map(colorOf);
		if (colors.length === 0) return FALLBACK;
		if (colors.length === 1) return colors[0];
		return `linear-gradient(to bottom, ${colors.join(', ')})`;
	});
	const maxCount = $derived(Math.max(1, ...tiers.map((t) => t.entities_count)));
	const totalCount = $derived(tiers.reduce((sum, t) => sum + t.entities_count, 0));
	const share = (count: number) => (totalCount ? Math.round((count / totalCount) * 100) : 0);

	async function callAction(name: string, fields: Record<string, string>): Promise<boolean> {
		busy = true;
		const body = new FormData();
		for (const [key, value] of Object.entries(fields)) body.append(key, value);
		try {
			const res = await fetch(`?/${name}`, {
				method: 'POST',
				body,
				headers: { 'x-sveltekit-action': 'true' }
			});
			const result = deserialize(await res.text());
			if (result.type !== 'success') {
				const detail =
					result.type === 'failure' ? (result.data?.error as Record<string, any>) : undefined;
				const message =
					detail?.error ?? detail?.detail ?? detail?.name?.[0] ?? detail?.rank?.[0] ?? undefined;
				toastStore.trigger({
					message: message ? safeTranslate(String(message)) : m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return false;
			}
			return true;
		} finally {
			await invalidateAll();
			busy = false;
		}
	}

	function update(tier: Tier, payload: Partial<Tier>) {
		return callAction('update', { id: tier.id, payload: JSON.stringify(payload) });
	}

	function persistOrder() {
		return callAction('reorder', { ids: JSON.stringify(tiers.map((t) => t.id)) });
	}

	function move(from: number, to: number) {
		if (to < 0 || to >= tiers.length || from === to) return;
		const next = [...tiers];
		const [moved] = next.splice(from, 1);
		next.splice(to, 0, moved);
		tiers = next;
		persistOrder();
	}

	async function addTier(event: SubmitEvent) {
		event.preventDefault();
		if (!newName.trim()) return;
		if (await callAction('create', { name: newName.trim(), hexcolor: newColor })) {
			newName = '';
		}
	}

	function onDrop(index: number) {
		if (dragIndex !== null) move(dragIndex, index);
		dragIndex = null;
	}
</script>

<div class="bg-surface-50-950 shadow-sm flex flex-col">
	<header
		class="flex flex-wrap items-start justify-between gap-4 px-6 pt-6 pb-5 border-b border-surface-200-800"
	>
		<div class="flex flex-col gap-1 max-w-2xl">
			<h1 class="text-2xl font-semibold tracking-tight text-surface-950-50">
				<i class="fa-solid fa-layer-group mr-2 text-surface-500"></i>{m.criticality()}
			</h1>
			<p class="text-sm text-surface-600-400">{m.tierScaleDescription()}</p>
		</div>
		<a
			href="/entities"
			class="text-sm text-primary-800-200 hover:text-primary-500 whitespace-nowrap pt-1"
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>{m.backToTable()}
		</a>
	</header>

	<div class="grid gap-8 p-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
		<!-- The ladder: order is the point, so it reads top (most critical) to bottom. -->
		<section class="relative pl-16" aria-label={m.criticality()}>
			<p class="mb-3 -ml-16 text-[11px] font-semibold uppercase tracking-[0.14em] text-surface-500">
				<i class="fa-solid fa-arrow-up mr-1.5"></i>{m.mostCritical()}
			</p>

			<!-- The rail runs from the first rung's number to the last one's. -->
			<div class="relative">
				<div
					class="rail absolute top-[1.375rem] bottom-[1.375rem] w-1.5 rounded-full"
					style="left: -2.8125rem; background: {railGradient}"
					aria-hidden="true"
				></div>
				<ol class="flex flex-col gap-2.5" data-testid="tier-scale">
					{#each tiers as tier, index (tier.id)}
						{@const color = colorOf(tier)}
						<li
							class="rung group relative {dragIndex === index ? 'opacity-40' : ''}"
							style="--tier: {color}; animation-delay: {index * 45}ms"
							draggable={canEdit && !busy}
							ondragstart={() => (dragIndex = index)}
							ondragend={() => (dragIndex = null)}
							ondragover={(e) => e.preventDefault()}
							ondrop={() => onDrop(index)}
							data-testid="tier-row"
						>
							<span
								class="rank absolute -left-16 top-1/2 -translate-y-1/2 grid place-items-center size-11 rounded-full border-2 bg-surface-50-950 {tier.is_visible
									? ''
									: 'border-dashed opacity-60'}"
								aria-hidden="true"
								><span class="size-3.5 rounded-full" style="background: var(--tier)"></span></span
							>

							<div
								class="flex flex-wrap items-center gap-3 rounded-xl border bg-surface-50-950 py-2.5 pl-4 pr-3 transition-shadow group-hover:shadow-md {tier.is_visible
									? 'border-surface-200-800 border-l-4'
									: 'border-dashed border-surface-300-700 border-l-4 opacity-70 grayscale'}"
								style="border-left-color: var(--tier)"
							>
								{#if canEdit}
									<div
										class="flex items-center gap-0.5 opacity-40 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
									>
										<span class="cursor-grab px-1 text-surface-400" aria-hidden="true">
											<i class="fa-solid fa-grip-vertical"></i>
										</span>
										<div class="flex flex-col">
											<button
												type="button"
												class="btn-icon btn-icon-sm h-5"
												aria-label={m.moveUp()}
												disabled={busy || index === 0}
												onclick={() => move(index, index - 1)}
											>
												<i class="fa-solid fa-chevron-up text-[10px]"></i>
											</button>
											<button
												type="button"
												class="btn-icon btn-icon-sm h-5"
												aria-label={m.moveDown()}
												disabled={busy || index === tiers.length - 1}
												onclick={() => move(index, index + 1)}
											>
												<i class="fa-solid fa-chevron-down text-[10px]"></i>
											</button>
										</div>
									</div>

									<!-- The swatch is the colour picker: the native input sits on top of it. -->
									<label
										class="swatch relative size-8 shrink-0 cursor-pointer rounded-full ring-2 ring-offset-2 ring-offset-surface-50-950 ring-transparent transition hover:ring-surface-300-700 focus-within:ring-primary-500"
										style="background: {color}"
									>
										<input
											type="color"
											class="absolute inset-0 size-full cursor-pointer opacity-0"
											value={color}
											aria-label={m.color()}
											disabled={busy}
											onchange={(e) => update(tier, { hexcolor: e.currentTarget.value })}
										/>
									</label>

									<input
										class="min-w-40 flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-base font-medium text-surface-950-50 outline-none transition hover:border-surface-300-700 focus:border-primary-500 focus:bg-surface-100-900"
										value={labelOf(tier)}
										aria-label={m.name()}
										disabled={busy}
										onchange={(e) => {
											const value = e.currentTarget.value.trim();
											if (value && value !== tier.name) update(tier, { name: value });
										}}
									/>
								{:else}
									<div class="flex-1 py-1"><TierBadge cell={tier} /></div>
								{/if}

								<!-- Weight of the tier: its share of the busiest one, in its own colour. -->
								<a
									class="flex min-w-36 items-center gap-2 text-sm text-surface-600-400 hover:text-primary-500"
									href={`/entities?tier=${tier.id}`}
									data-testid="tier-entities-count"
								>
									<span class="h-1.5 w-16 overflow-hidden rounded-full bg-surface-200-800">
										<span
											class="block h-full rounded-full transition-[width] duration-500"
											style="width: {(tier.entities_count / maxCount) *
												100}%; background: var(--tier)"
										></span>
									</span>
									<span class="tabular-nums whitespace-nowrap"
										>{m.entitiesCountLabel({ count: tier.entities_count })}</span
									>
								</a>

								{#if canEdit}
									<button
										type="button"
										class="btn-icon btn-icon-sm {tier.is_visible
											? 'text-surface-500'
											: 'text-warning-600-400'}"
										aria-pressed={!tier.is_visible}
										aria-label={tier.is_visible ? m.hide() : m.show()}
										title={tier.is_visible ? m.visible() : m.hidden()}
										disabled={busy}
										onclick={() => update(tier, { is_visible: !tier.is_visible })}
									>
										<i class="fa-solid {tier.is_visible ? 'fa-eye' : 'fa-eye-slash'}"></i>
									</button>
								{:else if !tier.is_visible}
									<span class="badge preset-tonal text-xs">{m.hidden()}</span>
								{/if}

								{#if canDelete && !tier.builtin}
									<button
										type="button"
										class="btn-icon btn-icon-sm text-error-500"
										aria-label={m.delete()}
										title={tier.entities_count || tier.solutions_count
											? m.tierInUseCannotDelete()
											: tier.in_history
												? m.tierInHistoryCannotDelete()
												: m.delete()}
										disabled={busy ||
											tier.entities_count > 0 ||
											!!tier.solutions_count ||
											tier.in_history}
										onclick={() => callAction('remove', { id: tier.id })}
									>
										<i class="fa-solid fa-trash"></i>
									</button>
								{/if}
							</div>
						</li>
					{/each}

					<!-- New tiers land at the bottom: the form is the next rung down. -->
					{#if canAdd}
						<li class="rung relative" style="animation-delay: {tiers.length * 45}ms">
							<span
								class="absolute -left-16 top-1/2 -translate-y-1/2 grid place-items-center size-11 rounded-full border-2 border-dashed border-surface-300-700 bg-surface-50-950 text-surface-400"
								aria-hidden="true"><i class="fa-solid fa-plus text-xs"></i></span
							>
							<form
								class="flex flex-wrap items-center gap-3 rounded-xl border-2 border-dashed border-surface-300-700 py-2 pl-4 pr-2 transition-colors focus-within:border-primary-500"
								onsubmit={addTier}
								data-testid="add-tier-form"
							>
								<label
									class="relative size-8 shrink-0 cursor-pointer rounded-full ring-2 ring-offset-2 ring-offset-surface-50-950 ring-transparent hover:ring-surface-300-700 focus-within:ring-primary-500"
									style="background: {HEX.test(newColor) ? newColor : FALLBACK}"
								>
									<input
										type="color"
										class="absolute inset-0 size-full cursor-pointer opacity-0"
										bind:value={newColor}
										aria-label={m.color()}
										disabled={busy}
									/>
								</label>
								<input
									class="min-w-40 flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-base outline-none placeholder:text-surface-400 focus:border-primary-500"
									bind:value={newName}
									placeholder={m.addTier()}
									aria-label={m.name()}
									disabled={busy}
									required
								/>
								<button
									class="btn btn-sm preset-filled-primary-500"
									type="submit"
									disabled={busy || !newName.trim()}
								>
									<i class="fa-solid fa-plus mr-1.5"></i>{m.addTier()}
								</button>
							</form>
						</li>
					{/if}
				</ol>
			</div>

			<p class="mt-3 -ml-16 text-[11px] font-semibold uppercase tracking-[0.14em] text-surface-500">
				<i class="fa-solid fa-arrow-down mr-1.5"></i>{m.leastCritical()}
			</p>
			<p class="mt-4 text-xs text-surface-500">{m.tierScaleOrderHint()}</p>
		</section>

		<aside class="flex flex-col gap-5">
			<!-- Where the vendors sit on the scale, as one strip of the scale's own colours. -->
			<section class="card bg-surface-100-900/60 p-4 flex flex-col gap-3">
				<h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-surface-500">
					{m.entitiesByTier()}
				</h2>
				<p class="-mt-1 text-xl font-semibold tabular-nums text-surface-950-50">
					{m.entitiesCountLabel({ count: totalCount })}
				</p>
				<div
					class="flex h-3 w-full overflow-hidden rounded-full bg-surface-200-800"
					aria-hidden="true"
				>
					{#each tiers.filter((t) => t.entities_count > 0) as tier (tier.id)}
						<span
							class="h-full transition-[flex-grow] duration-500 first:rounded-l-full last:rounded-r-full"
							style="flex-grow: {tier.entities_count}; background: {colorOf(tier)}"
							title="{labelOf(tier)}: {tier.entities_count}"
						></span>
					{/each}
				</div>
				<ul class="flex flex-col gap-1.5 text-sm">
					{#each tiers.filter((t) => t.is_visible || t.entities_count > 0) as tier (tier.id)}
						<li class="flex items-center gap-2">
							<span class="size-2.5 shrink-0 rounded-full" style="background: {colorOf(tier)}"
							></span>
							<a
								class="flex-1 truncate hover:text-primary-500 {tier.is_visible
									? 'text-surface-800-200'
									: 'text-surface-500 line-through'}"
								href={`/entities?tier=${tier.id}`}>{labelOf(tier)}</a
							>
							<span class="tabular-nums text-surface-600-400">{tier.entities_count}</span>
							<span class="w-10 text-right tabular-nums text-xs text-surface-500"
								>{share(tier.entities_count)}%</span
							>
						</li>
					{/each}
				</ul>
				<a class="text-sm text-primary-800-200 hover:text-primary-500" href="/entities?tier=--">
					<i class="fa-regular fa-circle mr-1.5 text-xs"></i>{m.untiered()}
					<i class="fa-solid fa-arrow-right ml-1 text-xs"></i>
				</a>
			</section>

			<section
				class="card bg-surface-100-900/60 p-4 flex flex-col gap-3"
				data-testid="tiers-fed-by"
			>
				<h2 class="text-xs font-semibold uppercase tracking-[0.14em] text-surface-500">
					{m.tiersFedBy()}
				</h2>
				{#if (data.fedBy ?? []).length === 0}
					<p class="text-sm text-surface-500">{m.tiersFedByNone()}</p>
					<a class="anchor text-sm" href="/libraries?object_type=quick_forms">{m.libraries()}</a>
				{:else}
					<ul class="flex flex-col gap-2.5 text-sm">
						{#each data.fedBy as quickForm (quickForm.id)}
							<li class="flex items-start gap-2.5">
								{#if quickForm.problems.length}
									<i
										class="fa-solid fa-triangle-exclamation mt-0.5 text-warning-600-400"
										aria-hidden="true"
									></i>
								{:else}
									<i class="fa-solid fa-circle-check mt-0.5 text-success-500" aria-hidden="true"
									></i>
								{/if}
								<div class="flex min-w-0 flex-col">
									<a class="anchor font-medium" href={`/quick-forms/${quickForm.id}`}
										>{quickForm.name}</a
									>
									{#if quickForm.library}
										<span class="truncate text-xs text-surface-500">{quickForm.library}</span>
									{/if}
									{#if quickForm.problems.length}
										<span class="text-xs text-warning-700 dark:text-warning-400">
											{quickForm.problems.map((p: string) => safeTranslate(p)).join(', ')}
										</span>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		</aside>
	</div>
</div>

<style>
	/* One staggered entrance for the ladder; nothing moves after that. */
	.rung {
		animation: rung-in 0.38s cubic-bezier(0.2, 0.7, 0.2, 1) both;
	}
	.rung .rank {
		border-color: var(--tier);
	}
	.rail {
		animation: rail-in 0.6s cubic-bezier(0.2, 0.7, 0.2, 1) both;
		transform-origin: top;
	}
	@keyframes rung-in {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes rail-in {
		from {
			transform: scaleY(0);
		}
		to {
			transform: scaleY(1);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.rung,
		.rail {
			animation: none;
		}
	}
</style>
