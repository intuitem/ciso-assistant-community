<script lang="ts">
	import { m } from '$paraglide/messages';

	interface SelectableItem {
		id: string;
		label: string;
	}

	interface Props {
		items: SelectableItem[];
		selectedIds: Set<string>;
		message?: string;
		classesMessage?: string;
	}

	let {
		items,
		selectedIds = $bindable(),
		message = '',
		classesMessage = 'bg-surface-100 bg-opacity-80 backdrop-blur-xs'
	}: Props = $props();

	let allSelected = $derived(items.length > 0 && selectedIds.size === items.length);

	function toggleAll() {
		if (allSelected) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(items.map((item) => item.id));
		}
	}

	function toggleItem(id: string) {
		const next = new Set(selectedIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		selectedIds = next;
	}
</script>

<article>
	{#if message}
		<p class="sticky top-0 p-2 {classesMessage}">{message}</p>
	{/if}
	{#if items.length > 1}
		<div class="px-4 py-2 border-b border-surface-300">
			<label class="flex items-center gap-2 cursor-pointer font-semibold text-sm">
				<input type="checkbox" checked={allSelected} onchange={toggleAll} class="checkbox" />
				{m.selectAll()} ({selectedIds.size}/{items.length})
			</label>
		</div>
	{/if}
	<ul class="ml-4 mr-4">
		{#each items as item (item.id)}
			<li class="py-1">
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="checkbox"
						checked={selectedIds.has(item.id)}
						onchange={() => toggleItem(item.id)}
						class="checkbox"
					/>
					<span>{item.label}</span>
				</label>
			</li>
		{/each}
	</ul>
</article>
