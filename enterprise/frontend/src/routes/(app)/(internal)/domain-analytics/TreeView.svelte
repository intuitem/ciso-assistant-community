<script module>
	// retain module scoped expansion state for each tree node
	const _expansionState = {
		/* treeNodeId: expanded <boolean> */
	};
</script>

<script>
	import TreeView from './TreeView.svelte';
	let { tree } = $props();
	const { name, children, uuid, viewable } = tree;
	let expanded = $state(_expansionState[name] || false);

	// Generate href from uuid if it exists
	const href = uuid ? `/domain-analytics/details/${uuid}/` : null;

	const toggleExpansion = () => {
		expanded = _expansionState[name] = !expanded;
	};
</script>

<ul data-testid="domain-analytics-treeview">
	<li>
		<div class="mb-1">
			<div class="flex flex-center">
				{#if children}
					<div
						class="flex items-center w-3 me-4 text-center cursor-pointer transition-transform duration-200 {!expanded
							? '-rotate-90'
							: ''}"
						onclick={toggleExpansion}
						data-testid="treeview-expand-arrow-elem"
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
							<path
								d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
							></path>
						</svg>
					</div>
				{:else}
					<span class="me-8"></span>
				{/if}
				{#if uuid && viewable}
					<a
						{href}
						class="text-xl font-semibold hover:text-primary-500 block"
						data-testid="treeview-label-text-elem">{name}</a
					>
				{:else}
					<p class="text-xl font-semibold" data-testid="treeview-label-text-elem">{name}</p>
				{/if}
			</div>
		</div>
		{#if expanded}
			{#each children as child}
				<TreeView tree={child} />
			{/each}
		{/if}
	</li>
</ul>

<style>
	ul {
		margin: 0;
		list-style: none;
		padding-left: 1.2rem;
		user-select: none;
	}
</style>
