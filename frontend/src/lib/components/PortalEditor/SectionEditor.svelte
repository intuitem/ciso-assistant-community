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

<section class="card bg-surface-50-950 p-5 space-y-4">
	<div class="flex items-center gap-2">
		<i class="fa-solid fa-layer-group text-surface-400"></i>
		<input
			bind:value={section.title}
			placeholder="Group title"
			class="input rounded-md font-semibold grow"
		/>
		<button
			onclick={() => onMoveSection(-1)}
			class="btn-icon btn-sm preset-tonal"
			aria-label="Move group up"><i class="fa-solid fa-chevron-up"></i></button
		>
		<button
			onclick={() => onMoveSection(1)}
			class="btn-icon btn-sm preset-tonal"
			aria-label="Move group down"><i class="fa-solid fa-chevron-down"></i></button
		>
		<button
			onclick={onRemoveSection}
			class="btn-icon btn-sm preset-tonal-error"
			aria-label={m.delete()}
			title={m.delete()}><i class="fa-solid fa-trash"></i></button
		>
	</div>

	<div class="space-y-3 pl-6">
		{#each section.items as item, ii}
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
		<button onclick={onAddItem} class="btn btn-sm preset-tonal">
			<i class="fa-solid fa-plus mr-1"></i>{m.addItem()}
		</button>
	</div>
</section>
