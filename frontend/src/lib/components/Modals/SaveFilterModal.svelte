<script lang="ts">
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';
	import { getModalStore, type ModalStore } from './stores';
	import { SAVED_FILTER_TARGET_MODELS } from '$lib/utils/savedFilters';

	const modalStore: ModalStore = getModalStore();

	interface DomainOption {
		id: string;
		name: string;
		depth: number;
	}

	interface Props {
		parent: any;
		urlModel: string;
		properties: Record<string, { value: string }[]>;
		onSaved: (entry: any, scope: 'personal' | 'shared') => void;
	}

	let { parent, urlModel, properties, onSaved }: Props = $props();

	let name = $state('');
	let scope = $state<'personal' | 'shared'>('personal');
	let domains = $state<DomainOption[]>([]);
	let selectedDomain = $state('');
	let domainsLoading = $state(true);
	let isSubmitting = $state(false);
	let errorMsg = $state<string | null>(null);

	function flatten(node: any, depth: number, out: DomainOption[]) {
		if (node.writable !== false && node.uuid) {
			out.push({ id: node.uuid, name: node.name, depth });
		}
		for (const child of node.children ?? []) {
			flatten(child, depth + 1, out);
		}
	}

	onMount(async () => {
		try {
			const res = await fetch(
				'/folders/org_tree/?include_perimeters=false&write_perm=add_savedfilter'
			);
			if (res.ok) {
				const tree = await res.json();
				const out: DomainOption[] = [];
				flatten(tree, 0, out);
				domains = out;
				if (domains.length) selectedDomain = domains[0].id;
			}
		} finally {
			domainsLoading = false;
		}
	});

	async function handleSubmit() {
		if (!name.trim()) return;
		isSubmitting = true;
		errorMsg = null;
		const model = SAVED_FILTER_TARGET_MODELS[urlModel];
		try {
			const endpoint = scope === 'personal' ? '/fe-api/saved-filters/personal/' : '/fe-api/saved-filters/';
			const body =
				scope === 'personal'
					? { name: name.trim(), model, properties }
					: { name: name.trim(), model, properties, folder: selectedDomain };
			const res = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			const data = await res.json();
			if (!res.ok) {
				errorMsg = typeof data === 'string' ? data : JSON.stringify(data);
				return;
			}
			onSaved(data, scope);
			parent.onClose();
		} finally {
			isSubmitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class="card bg-surface-50-950 p-4 w-modal shadow-xl space-y-4">
		<div class="flex items-center justify-between">
			<header class="text-2xl font-bold">{$modalStore[0].title ?? m.saveFilter()}</header>
			<button
				type="button"
				aria-label={m.close()}
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>

		<div class="space-y-1">
			<label class="block text-sm font-semibold" for="save-filter-name">{m.name()}</label>
			<input id="save-filter-name" type="text" class="input w-full" bind:value={name} />
		</div>

		<div class="space-y-1">
			<span class="block text-sm font-semibold">{m.scope()}</span>
			<div class="flex gap-4">
				<label class="flex items-center gap-2">
					<input type="radio" name="save-filter-scope" value="personal" bind:group={scope} />
					{m.personalFilters()}
				</label>
				<label class="flex items-center gap-2">
					<input type="radio" name="save-filter-scope" value="shared" bind:group={scope} />
					{m.sharedFilters()}
				</label>
			</div>
		</div>

		{#if scope === 'shared'}
			<div class="space-y-1">
				<label class="block text-sm font-semibold" for="save-filter-domain">{m.domain()}</label>
				{#if domainsLoading}
					<p class="text-sm text-surface-500">{m.loading()}...</p>
				{:else if domains.length === 0}
					<p class="text-sm text-surface-500">{m.noDomainsAvailable()}</p>
				{:else}
					<select id="save-filter-domain" class="select w-full" bind:value={selectedDomain}>
						{#each domains as domain (domain.id)}
							<option value={domain.id}>{'—'.repeat(domain.depth)} {domain.name}</option>
						{/each}
					</select>
				{/if}
			</div>
		{/if}

		{#if errorMsg}
			<p class="text-error-500 text-sm">{errorMsg}</p>
		{/if}

		<div class="flex justify-end gap-2">
			<button type="button" class="btn preset-tonal" onclick={parent.onClose}>
				{m.cancel()}
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={isSubmitting ||
					!name.trim() ||
					(scope === 'shared' && (domainsLoading || !selectedDomain))}
				onclick={handleSubmit}
			>
				{m.save()}
			</button>
		</div>
	</div>
{/if}
