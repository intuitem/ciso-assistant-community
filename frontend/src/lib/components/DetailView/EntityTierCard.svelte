<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import TierBadge from '$lib/components/ModelTable/field/TierBadge.svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { canPerformActionOnObject, hasPermissionAnywhere } from '$lib/utils/access-control';
	import { formatDate } from '$lib/utils/datetime';
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

	// Forms the viewer may fill in-house, else publications they may file,
	// that set this entity's tier.
	type Option = { kind: 'form' | 'publication'; id: string; name: string };
	let assessments: Option[] | null = $state(null);
	let choosing = $state(false);
	const canPublish = $derived(hasPermissionAnywhere(page.data.user, 'add_quickformpublication'));
	$effect(() => {
		if (entity.builtin) return;
		// Aborted when the entity changes, so a late answer cannot land on another one.
		const controller = new AbortController();
		fetch(`/entities/${entity.id}/assess-tier`, { signal: controller.signal })
			.then((res) => (res.ok ? res.json() : []))
			.then((rows) => (assessments = Array.isArray(rows) ? rows : []))
			.catch(() => {
				if (!controller.signal.aborted) assessments = [];
			});
		return () => controller.abort();
	});

	function startAssessing() {
		if (assessments?.length === 1) assess(assessments[0]);
		else choosing = !choosing;
	}

	// One start at a time: a double click must not open two drafts.
	let starting = $state(false);

	async function assess(option: Option) {
		if (starting) return;
		starting = true;
		try {
			const res = await fetch(`/entities/${entity.id}/assess-tier`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ kind: option.kind, id: option.id })
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
		} catch {
			toastStore.trigger({ message: m.anErrorOccurred(), background: 'preset-filled-error-500' });
		} finally {
			starting = false;
		}
	}

	// One sentence per source: who or what set the tier, and when.
	function tierOrigin(e: Record<string, any>): string {
		const date = e.tier_set_at ? formatDate(new Date(e.tier_set_at), false, getLocale()) : '';
		if (!date) return safeTranslate(e.tier_source);
		if (e.tier_source === 'assessment') return m.tierAssessedOn({ date });
		if (e.tier_source === 'override') return m.tierAdjustedOn({ date });
		return m.tierSetManuallyOn({ date });
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
		{#if !editing}
			<div class="flex flex-wrap justify-end gap-2">
				{#if assessments?.length}
					<button
						type="button"
						class="btn btn-sm preset-filled-primary-500"
						onclick={startAssessing}
						disabled={starting}
						aria-expanded={assessments.length > 1 ? choosing : undefined}
						data-testid="assess-tier-button"
					>
						<i class="fa-solid fa-clipboard-check mr-1"></i>{m.assessTier()}
						{#if assessments.length > 1}<i class="fa-solid fa-caret-down ml-1"></i>{/if}
					</button>
				{/if}
				{#if canChange}
					<button
						type="button"
						class="btn btn-sm preset-tonal-primary"
						onclick={startEditing}
						data-testid="change-tier-button"
					>
						<i class="fa-solid fa-hand-point-up mr-1"></i>{m.changeTier()}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	{#if choosing && !editing && assessments}
		<ul class="flex flex-col gap-1 rounded-base border border-surface-200-800 p-1">
			{#each assessments as option (option.id)}
				<li>
					<button
						type="button"
						class="btn btn-sm w-full justify-start hover:preset-tonal"
						onclick={() => assess(option)}
						disabled={starting}
						data-testid="assess-tier-option">{option.name}</button
					>
				</li>
			{/each}
		</ul>
	{/if}

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
			<span class="text-sm text-surface-600-400">
				{tierOrigin(entity)}
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

	{#if !editing && assessments?.length === 0}
		<p class="border-t border-surface-200-800 pt-3 text-xs text-surface-500">
			{m.noTierFormPublished()}
			{#if canPublish}
				<a class="anchor" href="/entities/tiers">{m.setOneUp()}</a>
			{/if}
		</p>
	{/if}
</div>
