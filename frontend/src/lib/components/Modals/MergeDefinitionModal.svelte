<script lang="ts">
	// Merge a definition into another: the metrics move, the definition goes.
	import { goto, invalidateAll } from '$app/navigation';
	import { m } from '#paraglide/messages.js';
	import { getModalStore, type ModalStore } from './stores';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { safeTranslate } from '#lib/utils/i18n.js';

	interface Props {
		parent: any;
		definition: any;
	}
	let { parent, definition }: Props = $props();
	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	type Candidate = {
		id: string;
		name: string;
		folder: { id: string; name: string };
		category: string;
		unit: { id: string; name: string } | null;
		domains: string[];
		is_derived: boolean;
	};
	let query = $state(String(definition?.name ?? ''));
	let candidates = $state<Candidate[]>([]);
	let into = $state('');
	let error = $state('');
	let busy = $state(false);
	let run = 0;

	$effect(() => {
		const name = query.trim();
		const current = ++run;
		if (name.length < 3) {
			candidates = [];
			return;
		}
		const timer = setTimeout(async () => {
			try {
				const params = new URLSearchParams({
					name,
					category: definition.category ?? '',
					exclude: definition.id,
					mergeable: '1'
				});
				const res = await fetch(`/fe-api/metrology/similar-definitions?${params}`);
				if (!res.ok || current !== run) return;
				candidates = await res.json();
			} catch {
				candidates = [];
			}
			// A target that left the list is no target.
			if (!candidates.some((c) => c.id === into)) into = '';
		}, 250);
		return () => clearTimeout(timer);
	});

	const sameUnit = (c: Candidate) => (c.unit?.id ?? null) === (definition.unit?.id ?? null);

	async function merge() {
		if (!into) return;
		busy = true;
		error = '';
		let data: Record<string, unknown> = {};
		try {
			const res = await fetch(`/fe-api/metrology/merge/${definition.id}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ into })
			});
			data = await res.json().catch(() => ({}));
			if (!res.ok) {
				const first = Object.values(data)[0];
				error = Array.isArray(first) ? safeTranslate(String(first[0])) : m.mergeRequirements();
				return;
			}
		} catch {
			error = m.mergeFailed();
			return;
		} finally {
			busy = false;
		}
		// Merged: what follows is navigation, never a merge failure.
		toastStore.trigger({
			message: m.mergeDone({ count: Number(data.moved ?? 0) }),
			background: 'preset-filled-success-500'
		});
		modalStore.close();
		await goto(`/metric-definitions/${data.into}`);
		await invalidateAll();
	}
</script>

{#if $modalStore[0]}
	<div
		class="card bg-surface-50-950 p-6 w-modal shadow-xl space-y-4"
		data-testid="merge-definition-modal"
	>
		<header class="flex items-center justify-between">
			<h2 class="text-xl font-bold">{m.mergeDefinition()}</h2>
			<button
				type="button"
				class="btn-icon preset-tonal"
				aria-label={m.close()}
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</header>
		<p class="text-sm text-surface-500">{m.mergeDefinitionHelpText()}</p>
		<div class="rounded-base border border-surface-200-800 p-3 text-sm">
			<span class="font-semibold">{definition.name}</span>
			<span class="text-surface-500">
				· {definition.folder?.str ?? definition.folder?.name ?? ''}</span
			>
		</div>
		<label class="flex flex-col gap-1 text-sm">
			<span class="font-semibold">{m.mergeTarget()}</span>
			<input class="input" bind:value={query} placeholder={m.mergeTargetSearch()} />
		</label>
		<div
			class="max-h-64 overflow-auto divide-y divide-surface-200-800 rounded-base border border-surface-200-800"
		>
			{#each candidates as candidate (candidate.id)}
				<label
					class="flex items-start gap-3 p-3 text-sm cursor-pointer {sameUnit(candidate)
						? ''
						: 'opacity-50'}"
				>
					<input
						type="radio"
						class="radio mt-1"
						name="into"
						value={candidate.id}
						bind:group={into}
						disabled={!sameUnit(candidate)}
					/>
					<span class="flex-1">
						<span class="font-semibold">{candidate.name}</span>
						<span class="text-surface-500">
							· {candidate.folder.name}{candidate.unit ? ` · ${candidate.unit.name}` : ''}</span
						>
						{#if candidate.domains.length}
							<span class="block text-xs text-surface-500"
								>{m.measuredIn({ domains: candidate.domains.join(', ') })}</span
							>
						{/if}
					</span>
				</label>
			{:else}
				<p class="p-3 text-sm text-surface-500 m-0">{m.noMatchingDefinition()}</p>
			{/each}
		</div>
		<p class="text-xs text-surface-500">{m.mergeRequirements()}</p>
		{#if error}
			<p class="text-sm text-error-500" role="alert">{error}</p>
		{/if}
		<footer class="flex justify-end gap-2">
			<button type="button" class="btn preset-tonal" onclick={parent.onClose}>{m.cancel()}</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				onclick={merge}
				disabled={!into || busy}
				data-testid="merge-confirm"
			>
				{m.mergeDefinitionAction()}
			</button>
		</footer>
	</div>
{/if}
