<script lang="ts">
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';
	import FilterNameModal from './FilterNameModal.svelte';

	interface DomainOption {
		id: string;
		name: string;
		depth: number;
	}

	interface Props {
		parent: any;
		model: string;
		properties: Record<string, { value: string }[]>;
		onSaved: (entry: any, scope: 'personal' | 'shared') => void;
	}

	let { parent, model, properties, onSaved }: Props = $props();

	let scope = $state<'personal' | 'shared'>('personal');
	let domains = $state<DomainOption[]>([]);
	let selectedDomain = $state('');
	let domainsLoading = $state(true);

	const canSubmit = $derived(scope !== 'shared' || (!domainsLoading && !!selectedDomain));

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

	async function handleSubmit(name: string) {
		const endpoint =
			scope === 'personal' ? '/fe-api/saved-filters/personal/' : '/fe-api/saved-filters/';
		const body =
			scope === 'personal'
				? { name, model, properties }
				: { name, model, properties, folder: selectedDomain };
		const res = await fetch(endpoint, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		const data = await res.json();
		if (!res.ok) {
			throw new Error(typeof data === 'string' ? data : JSON.stringify(data));
		}
		onSaved(data, scope);
	}
</script>

<FilterNameModal {parent} {canSubmit} onSubmit={handleSubmit}>
	{#snippet extraFields()}
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
	{/snippet}
</FilterNameModal>
