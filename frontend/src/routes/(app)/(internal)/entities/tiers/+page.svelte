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
	<div class="flex justify-between items-center p-4 border-b border-surface-200-800">
		<h1 class="text-2xl font-semibold text-surface-950-50">
			<i class="fa-solid fa-layer-group mr-2"></i>
			{m.tierScale()}
		</h1>
		<a href="/entities" class="text-primary-800-200 hover:text-primary-500 cursor-pointer">
			<i class="fa-solid fa-arrow-left mr-2"></i>
			{m.backToTable()}
		</a>
	</div>

	<div class="p-4 flex flex-col gap-4 max-w-3xl">
		<p class="text-sm text-surface-600-400">{m.tierScaleDescription()}</p>

		<ol class="flex flex-col gap-2" aria-label={m.tierScale()} data-testid="tier-scale">
			{#each tiers as tier, index (tier.id)}
				<li
					class="flex flex-wrap items-center gap-3 rounded-lg border border-surface-200-800 bg-surface-50-950 px-3 py-2 {dragIndex ===
					index
						? 'opacity-50'
						: ''} {tier.is_visible ? '' : 'opacity-60'}"
					draggable={canEdit && !busy}
					ondragstart={() => (dragIndex = index)}
					ondragend={() => (dragIndex = null)}
					ondragover={(e) => e.preventDefault()}
					ondrop={() => onDrop(index)}
					data-testid="tier-row"
				>
					{#if canEdit}
						<span class="cursor-grab text-surface-400" aria-hidden="true">
							<i class="fa-solid fa-grip-vertical"></i>
						</span>
						<div class="flex flex-col">
							<button
								type="button"
								class="btn-icon btn-icon-sm"
								aria-label={m.moveUp()}
								disabled={busy || index === 0}
								onclick={() => move(index, index - 1)}
							>
								<i class="fa-solid fa-chevron-up text-xs"></i>
							</button>
							<button
								type="button"
								class="btn-icon btn-icon-sm"
								aria-label={m.moveDown()}
								disabled={busy || index === tiers.length - 1}
								onclick={() => move(index, index + 1)}
							>
								<i class="fa-solid fa-chevron-down text-xs"></i>
							</button>
						</div>
					{/if}

					<div class="w-28">
						<TierBadge cell={tier} />
					</div>

					{#if canEdit}
						<input
							class="input flex-1 min-w-40"
							value={tier.builtin ? safeTranslate(tier.name) : tier.name}
							aria-label={m.name()}
							disabled={busy}
							onchange={(e) => {
								const value = e.currentTarget.value.trim();
								if (value && value !== tier.name) update(tier, { name: value });
							}}
						/>
						<input
							type="color"
							class="h-9 w-12 cursor-pointer rounded"
							value={tier.hexcolor || '#94a3b8'}
							aria-label={m.color()}
							disabled={busy}
							onchange={(e) => update(tier, { hexcolor: e.currentTarget.value })}
						/>
						<label class="flex items-center gap-1 text-sm">
							<input
								type="checkbox"
								class="checkbox"
								checked={tier.is_visible}
								disabled={busy}
								onchange={(e) => update(tier, { is_visible: e.currentTarget.checked })}
							/>
							{m.isVisible()}
						</label>
					{:else}
						<span class="flex-1">{safeTranslate(tier.name)}</span>
					{/if}

					<a
						class="text-sm anchor whitespace-nowrap"
						href={`/entities?tier=${tier.id}`}
						data-testid="tier-entities-count"
					>
						{m.entitiesCountLabel({ count: tier.entities_count })}
					</a>

					{#if canDelete && !tier.builtin}
						<button
							type="button"
							class="btn-icon btn-icon-sm text-error-500"
							aria-label={m.delete()}
							title={tier.entities_count ? m.tierInUseCannotDelete() : m.delete()}
							disabled={busy || tier.entities_count > 0}
							onclick={() => callAction('remove', { id: tier.id })}
						>
							<i class="fa-solid fa-trash"></i>
						</button>
					{/if}
				</li>
			{/each}
		</ol>
		<p class="text-xs text-surface-500">{m.tierScaleOrderHint()}</p>

		<section class="flex flex-col gap-2 pt-2" data-testid="tiers-fed-by">
			<h2 class="text-sm font-semibold uppercase tracking-wider text-surface-500">
				{m.tiersFedBy()}
			</h2>
			{#if (data.fedBy ?? []).length === 0}
				<p class="text-sm text-surface-500">{m.tiersFedByNone()}</p>
			{:else}
				<ul class="flex flex-col gap-1 text-sm">
					{#each data.fedBy as publication (publication.id)}
						<li class="flex flex-wrap items-center gap-2">
							<a class="anchor" href={`/quick-form-publications/${publication.id}`}
								>{publication.name}</a
							>
							<span class="text-surface-500">· {publication.quick_form} · {publication.domain}</span
							>
							{#if !publication.enabled}
								<span class="badge preset-tonal text-xs">{m.disabled()}</span>
							{/if}
							{#if publication.problems.length}
								<span class="text-warning-700 dark:text-warning-400 text-xs">
									<i class="fa-solid fa-triangle-exclamation mr-1"></i>{publication.problems
										.map((p: string) => safeTranslate(p))
										.join(', ')}
								</span>
							{:else}
								<i class="fa-solid fa-circle-check text-success-500 text-xs"></i>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		{#if canAdd}
			<form class="flex flex-wrap items-end gap-2" onsubmit={addTier} data-testid="add-tier-form">
				<label class="label flex-1 min-w-40">
					<span class="text-sm font-semibold">{m.name()}</span>
					<input class="input" bind:value={newName} disabled={busy} required />
				</label>
				<label class="label">
					<span class="text-sm font-semibold">{m.color()}</span>
					<input
						type="color"
						class="h-10 w-14 cursor-pointer rounded"
						bind:value={newColor}
						disabled={busy}
					/>
				</label>
				<button class="btn preset-filled-primary-500" type="submit" disabled={busy}>
					<i class="fa-solid fa-plus mr-2"></i>{m.addTier()}
				</button>
			</form>
		{/if}
	</div>
</div>
