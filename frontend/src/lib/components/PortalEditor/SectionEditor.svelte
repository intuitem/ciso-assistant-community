<script lang="ts">
	import { m } from '$paraglide/messages';
	import TileEditor from './TileEditor.svelte';

	type Item = {
		id?: string;
		icon: string;
		title: string;
		description: string;
		kind: string;
		target: Record<string, any>;
	};
	type Section = { title: string; description: string; items: Item[] };

	let {
		section,
		sections,
		si,
		ctx,
		onMoveSection,
		onRemoveSection,
		onAddItem,
		onMoveItem,
		onRemoveItem,
		onMoveToGroup,
		onUpload
	}: {
		section: Section;
		sections: Section[];
		si: number;
		ctx: any;
		onMoveSection: (dir: -1 | 1) => void;
		onRemoveSection: () => void;
		onAddItem: () => void;
		onMoveItem: (ii: number, dir: -1 | 1) => void;
		onRemoveItem: (ii: number) => void;
		onMoveToGroup: (ii: number, targetSi: number) => void;
		onUpload: (item: Item, e: Event) => void;
	} = $props();
</script>

<section
	class="overflow-hidden rounded-xl border border-l-4 border-surface-200-800 border-l-primary-500 bg-surface-50-950 shadow-sm"
>
	<header
		class="flex items-center gap-3 border-b border-surface-200-800 bg-surface-50-950 px-4 py-3"
	>
		<span
			class="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-primary-500"
		>
			<i class="fa-solid fa-layer-group text-sm"></i>
		</span>
		<input
			bind:value={section.title}
			placeholder={m.groupTitle()}
			aria-label={m.groupTitle()}
			class="min-w-0 grow rounded-md border border-transparent bg-transparent px-2 py-1 text-base font-semibold hover:bg-surface-100-900 focus:border-surface-300-700 focus:bg-surface-100-900 focus:outline-none"
		/>
		<span
			class="rounded-full bg-surface-200-800 px-2 py-0.5 text-xs font-medium tabular-nums text-surface-600-400"
			>{section.items.length}</span
		>
		<div class="flex gap-1">
			<button
				onclick={() => onMoveSection(-1)}
				class="btn-icon btn-sm preset-tonal"
				aria-label={m.moveGroupUp()}><i class="fa-solid fa-chevron-up"></i></button
			>
			<button
				onclick={() => onMoveSection(1)}
				class="btn-icon btn-sm preset-tonal"
				aria-label={m.moveGroupDown()}><i class="fa-solid fa-chevron-down"></i></button
			>
			<button
				onclick={onRemoveSection}
				class="btn-icon btn-sm preset-tonal-error"
				aria-label={m.delete()}
				title={m.delete()}><i class="fa-solid fa-trash"></i></button
			>
		</div>
	</header>

	<!-- Tinted well: tiles read as cards nested inside the group. -->
	<div class="space-y-3 bg-surface-200-800/50 p-4">
		<!-- Keyed on the object: ids are optional, and unkeyed the per-tile form state
		     would land on a neighbour when reordering. -->
		{#each section.items as item, ii (item)}
			<TileEditor
				{item}
				{ctx}
				{sections}
				{si}
				{ii}
				onMoveItem={(dir) => onMoveItem(ii, dir)}
				onRemoveItem={() => onRemoveItem(ii)}
				onMoveToGroup={(targetSi) => onMoveToGroup(ii, targetSi)}
				{onUpload}
			/>
		{/each}
		<button
			onclick={onAddItem}
			class="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-surface-300-700 py-3 text-sm font-medium text-surface-600-400 transition-colors hover:border-primary-400 hover:text-primary-500"
		>
			<i class="fa-solid fa-plus"></i>{m.addItem()}
		</button>
	</div>
</section>
