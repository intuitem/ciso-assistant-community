<script module lang="ts">
	export type CascadeObject = { id: string; name: string };
	export type CascadeGroup = {
		model: string;
		verbose_name?: string;
		/** Objects in the group when `objects` holds only some of them. */
		count?: number;
		objects: CascadeObject[];
	};
</script>

<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import { SvelteSet } from 'svelte/reactivity';

	interface Props {
		groups: CascadeGroup[];
		/** Prefixes the element ids, so two lists in one modal stay distinct. */
		idPrefix: string;
	}

	let { groups, idPrefix }: Props = $props();

	const expanded = new SvelteSet<string>();
	function toggle(model: string): void {
		if (expanded.has(model)) expanded.delete(model);
		else expanded.add(model);
	}
</script>

{#each groups as group (group.model)}
	{@const total = group.count ?? group.objects.length}
	<section class="border-t border-surface-200-800">
		<button
			type="button"
			class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-50-950 text-sm"
			aria-controls={`${idPrefix}-${group.model}`}
			aria-expanded={expanded.has(group.model)}
			onclick={() => toggle(group.model)}
		>
			<span class="font-medium text-surface-950-50">{group.verbose_name ?? group.model}</span>
			<span class="text-xs text-surface-600-400">
				{total}
			</span>
		</button>

		{#if expanded.has(group.model)}
			<ul id={`${idPrefix}-${group.model}`} class="px-3 pb-2 text-sm space-y-0.5 bg-surface-50-950">
				{#each group.objects as o (o.id)}
					<li class="flex items-center justify-between py-1">
						<span class="truncate text-surface-700-300" title={o.name}>{o.name}</span>
					</li>
				{/each}
				{#if total > group.objects.length}
					<li class="py-1 text-xs text-surface-600-400">
						{m.andNMoreObjects({ count: total - group.objects.length })}
					</li>
				{/if}
			</ul>
		{/if}
	</section>
{/each}
