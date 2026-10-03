<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import TierBadge from '$lib/components/ModelTable/field/TierBadge.svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { canPerformActionOnObject } from '$lib/utils/access-control';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { safeTranslate } from '$lib/utils/i18n';
	import { getLocale } from '$paraglide/runtime';
	import { m } from '$paraglide/messages';

	interface Props {
		entity: Record<string, any>;
	}

	let { entity }: Props = $props();

	const toastStore = getToastStore();

	const canChange = $derived(
		!entity.builtin &&
			canPerformActionOnObject({
				user: page.data.user,
				action: 'change',
				model: 'entity',
				object: entity
			})
	);

	// Publications the viewer may file that set this entity's tier.
	let assessments: { id: string; name: string }[] = $state([]);
	$effect(() => {
		if (entity.builtin) return;
		fetch(`/entities/${entity.id}/assess-tier`)
			.then((res) => (res.ok ? res.json() : []))
			.then((rows) => (assessments = rows));
	});

	async function assess(publication: string) {
		const res = await fetch(`/entities/${entity.id}/assess-tier`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ publication })
		});
		const body = await res.json().catch(() => ({}));
		if (!res.ok || !body.redirect) {
			toastStore.trigger({
				message: body.error ? safeTranslate(body.error) : m.anErrorOccurred(),
				background: 'preset-filled-error-500'
			});
			return;
		}
		await goto(body.redirect);
	}

	let editing = $state(false);
	let saving = $state(false);
	let options: { id: string; name: string }[] = $state([]);
	let selected = $state('');
	let note = $state('');

	async function startEditing() {
		// Visible tiers plus the current one even when hidden, so Save without a
		// change keeps it.
		const res = await fetch(`/tiers?selectable=${entity.tier?.id ?? ''}`);
		const data = res.ok ? await res.json() : {};
		options = data.results ?? data ?? [];
		selected = entity.tier?.id ?? '';
		note = '';
		editing = true;
	}

	async function save() {
		saving = true;
		try {
			const res = await fetch(`/entities/${entity.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ tier: selected || null, tier_note: note })
			});
			if (!res.ok) {
				toastStore.trigger({
					message: m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			editing = false;
			await invalidateAll();
		} finally {
			saving = false;
		}
	}
</script>

<div
	class="card p-4 bg-surface-50-950 border border-surface-200-800 flex flex-col gap-3"
	data-testid="entity-tier-card"
>
	<div class="flex items-center justify-between">
		<h3 class="font-semibold text-surface-950-50">
			<i class="fa-solid fa-layer-group mr-2"></i>{m.tier()}
		</h3>
		{#if canChange && !editing}
			<button
				type="button"
				class="btn btn-sm preset-tonal-primary"
				onclick={startEditing}
				data-testid="change-tier-button"
			>
				<i class="fa-solid fa-pen mr-1"></i>{m.changeTier()}
			</button>
		{/if}
	</div>

	{#if editing}
		<label class="label">
			<span class="text-sm font-semibold">{m.tier()}</span>
			<select class="select" bind:value={selected} disabled={saving}>
				<option value="">--</option>
				{#each options as option (option.id)}
					<option value={option.id}>{safeTranslate(option.name)}</option>
				{/each}
			</select>
		</label>
		<label class="label">
			<span class="text-sm font-semibold">{m.tierNote()}</span>
			<input class="input" bind:value={note} disabled={saving} />
			<span class="text-xs text-surface-500">{m.tierNoteHelpText()}</span>
		</label>
		<div class="flex gap-2 justify-end">
			<button
				type="button"
				class="btn btn-sm preset-tonal"
				disabled={saving}
				onclick={() => (editing = false)}>{m.cancel()}</button
			>
			<button
				type="button"
				class="btn btn-sm preset-filled-primary-500"
				disabled={saving}
				onclick={save}
				data-testid="save-tier-button">{m.save()}</button
			>
		</div>
	{:else if entity.tier}
		<div class="flex flex-wrap items-center gap-3">
			<TierBadge cell={entity.tier} />
			{#if entity.tier_value !== null && entity.tier_value !== undefined}
				<span class="font-mono text-sm" title={m.tierValue()}
					>{Number.isInteger(entity.tier_value)
						? entity.tier_value
						: entity.tier_value.toFixed(2)}</span
				>
			{/if}
			<span class="text-sm text-surface-600-400">
				{safeTranslate(entity.tier_source)}
				{#if entity.tier_set_at}
					· {formatDateOrDateTime(entity.tier_set_at, getLocale())}
				{/if}
				{#if entity.tier_response?.id}
					· <a class="anchor" href={`/quick-form-responses/${entity.tier_response.id}`}
						>{entity.tier_response.ref_id ?? m.tierAssessment()}</a
					>
				{/if}
			</span>
		</div>
	{:else}
		<p class="text-sm text-surface-600-400">{m.noTierYet()}</p>
	{/if}

	{#if !editing && assessments.length}
		<div class="flex flex-wrap gap-2 border-t border-surface-200-800 pt-3">
			{#each assessments as publication (publication.id)}
				<button
					type="button"
					class="btn btn-sm preset-tonal-secondary"
					onclick={() => assess(publication.id)}
					data-testid="assess-tier-button"
				>
					<i class="fa-solid fa-clipboard-check mr-1"></i>{assessments.length === 1
						? m.assessTier()
						: publication.name}
				</button>
			{/each}
		</div>
	{/if}
</div>
