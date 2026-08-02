<script lang="ts">
	import { untrack } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Option {
		id: string;
		label: string;
	}

	interface Props {
		label: string;
		/** SvelteKit proxy path, e.g. `assets` */
		endpoint: string;
		value: string[];
		onChange: (ids: string[]) => void;
		disabled?: boolean;
	}

	let { label, endpoint, value, onChange, disabled = false }: Props = $props();

	let query = $state('');
	let results = $state<Option[]>([]);
	let chosen = $state<Option[]>([]);
	let loading = $state(false);
	let open = $state(false);
	let timer: ReturnType<typeof setTimeout> | null = null;

	// AutocompleteSelect needs a Superforms context, which this panel has none of
	function labelOf(item: any): string {
		const name = [item.ref_id, item.name].filter(Boolean).join(' - ') || item.str || item.id;
		return item.folder?.str ? `${item.folder.str}/${name}` : name;
	}

	async function fetchPage(params: string): Promise<Option[]> {
		const res = await fetch(`/${endpoint}?${params}`);
		if (!res.ok) return [];
		const data = await res.json();
		return (data?.results ?? data ?? []).map((item: any) => ({
			id: item.id,
			label: labelOf(item)
		}));
	}

	// stored ids resolve to labels independently of the search
	$effect(() => {
		const ids = value;
		untrack(() => resolveLabels(ids));
	});

	function resolveLabels(ids: string[]) {
		if (!ids.length) {
			chosen = [];
			return;
		}
		const missing = ids.filter((id) => !chosen.some((item) => item.id === id));
		if (!missing.length) {
			chosen = chosen.filter((item) => ids.includes(item.id));
			return;
		}
		fetchPage(`id=${missing.join(',')}&limit=${missing.length}`).then((items) => {
			const known = new Map([...chosen, ...items].map((item) => [item.id, item]));
			chosen = ids.map((id) => known.get(id) ?? { id, label: id }).filter(Boolean);
		});
	}

	function search() {
		if (timer) clearTimeout(timer);
		timer = setTimeout(async () => {
			loading = true;
			results = await fetchPage(`search=${encodeURIComponent(query)}&limit=25`);
			loading = false;
		}, 250);
	}

	function toggle(option: Option) {
		onChange(
			value.includes(option.id) ? value.filter((id) => id !== option.id) : [...value, option.id]
		);
	}
</script>

<div class="space-y-1">
	<span class="text-xs font-semibold text-surface-700-300">{label}</span>

	{#if chosen.length}
		<div class="flex flex-wrap gap-1">
			{#each chosen as item (item.id)}
				<span class="badge preset-tonal-secondary text-[10px]">
					{item.label}
					{#if !disabled}
						<button
							type="button"
							class="ml-1"
							aria-label="{m.remove()} {item.label}"
							onclick={() => onChange(value.filter((id) => id !== item.id))}>✕</button
						>
					{/if}
				</span>
			{/each}
		</div>
	{/if}

	{#if !disabled}
		<input
			type="search"
			class="input w-full px-2 py-1 text-xs"
			placeholder={m.searchPlaceholder()}
			bind:value={query}
			oninput={() => {
				open = true;
				search();
			}}
			onfocus={() => {
				open = true;
				if (!results.length) search();
			}}
		/>
		{#if open && (results.length || loading)}
			<ul
				class="max-h-40 overflow-y-auto rounded-base border border-surface-300-700 bg-surface-50-950 text-xs"
			>
				{#if loading}
					<li class="px-2 py-1 text-surface-500 italic">{m.loading()}</li>
				{:else}
					{#each results as option (option.id)}
						<li>
							<button
								type="button"
								class="flex w-full items-center gap-2 px-2 py-1 text-left hover:bg-surface-100-900"
								aria-pressed={value.includes(option.id)}
								onclick={() => toggle(option)}
							>
								<i
									class="fa-{value.includes(option.id)
										? 'solid fa-square-check text-primary-500'
										: 'regular fa-square text-surface-500'} text-xs"
								></i>
								<span class="grow">{option.label}</span>
							</button>
						</li>
					{/each}
				{/if}
			</ul>
		{/if}
	{/if}
</div>
