<script lang="ts">
	import { m } from '$paraglide/messages';
	import FilterNameModal from './FilterNameModal.svelte';
	import { hasPermissionAnywhere } from '$lib/utils/access-control';
	import type { User } from '$lib/utils/types';

	interface DomainOption {
		id: string;
		name: string;
		depth: number;
	}

	interface Props {
		parent: any;
		user?: User;
		initialName: string;
		// fields to share the filter to a domain
		filterId?: string;
		model?: string;
		properties?: Record<string, { value: string }[]>;
		onRenamed: (name: string) => void | Promise<void>;
		onShared?: (result: { shared: any; personal: any }) => void;
	}

	let { parent, user, initialName, filterId, model, properties, onRenamed, onShared }: Props =
		$props();

	const canShare = !!(
		filterId &&
		model &&
		onShared &&
		user &&
		hasPermissionAnywhere(user, 'add_savedfilter')
	);

	// Activate the sharing saved filter. When enabled, the user can choose a domain that the filter will be saved to when the modifications are saved.
	let shareEnabled = $state(false);
	let domains = $state<DomainOption[]>([]);
	let domainsLoading = $state(false);
	let selectedDomain = $state('');

	const canSubmit = $derived(!shareEnabled || (!domainsLoading && !!selectedDomain));

	function flatten(node: any, depth: number, out: DomainOption[]) {
		if (node.writable !== false && node.uuid) {
			out.push({ id: node.uuid, name: node.name, depth });
		}
		for (const child of node.children ?? []) {
			flatten(child, depth + 1, out);
		}
	}

	async function enableShare() {
		shareEnabled = true;
		if (domains.length || domainsLoading) {
			return;
		}
		domainsLoading = true;
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
	}

	function disableShare() {
		shareEnabled = false;
		selectedDomain = '';
	}

	async function handleSubmit(name: string) {
		await onRenamed(name);
		if (!shareEnabled || !selectedDomain) {
			return;
		}

		const sharedRes = await fetch('/fe-api/saved-filters/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, model, properties, folder: selectedDomain })
		});
		const shared = await sharedRes.json();
		if (!sharedRes.ok) {
			throw new Error(typeof shared === 'string' ? shared : JSON.stringify(shared));
		}

		const linkRes = await fetch(`/fe-api/saved-filters/personal/${filterId}/link/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ shared_id: shared.id })
		});
		const personal = await linkRes.json();
		if (!linkRes.ok) {
			throw new Error(typeof personal === 'string' ? personal : JSON.stringify(personal));
		}

		onShared?.({ shared, personal });
	}
</script>

<FilterNameModal {parent} {initialName} {canSubmit} onSubmit={handleSubmit}>
	{#snippet extraFields()}
		{#if canShare}
			<div class="space-y-2 pt-2 border-t border-surface-200-800">
				{#if !shareEnabled}
					<button type="button" class="btn btn-sm preset-tonal-surface" onclick={enableShare}>
						<i class="fa-solid fa-share-nodes mr-2"></i>{m.shareToDomain()}
					</button>
				{:else}
					<div class="flex items-center justify-between">
						<span class="block text-sm font-semibold">{m.shareToDomain()}</span>
						<button
							type="button"
							class="text-surface-500 hover:text-surface-700-300 text-sm"
							onclick={disableShare}
						>
							<i class="fa-solid fa-xmark"></i>
						</button>
					</div>
					{#if domainsLoading}
						<p class="text-sm text-surface-500">{m.loading()}...</p>
					{:else if domains.length === 0}
						<p class="text-sm text-surface-500">{m.noDomainsAvailable()}</p>
					{:else}
						<select class="select w-full" bind:value={selectedDomain}>
							{#each domains as domain (domain.id)}
								<option value={domain.id}>{'—'.repeat(domain.depth)} {domain.name}</option>
							{/each}
						</select>
					{/if}
				{/if}
			</div>
		{/if}
	{/snippet}
</FilterNameModal>
