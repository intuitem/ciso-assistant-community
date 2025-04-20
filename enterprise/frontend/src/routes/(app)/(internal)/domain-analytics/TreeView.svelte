<script context="module">
	// retain module scoped expansion state for each tree node
	const _expansionState = {
		/* treeNodeId: expanded <boolean> */
	};
</script>

<script>
	export let tree;
	const { name, children, uuid } = tree;
	let expanded = _expansionState[name] || false;

	// Generate href from uuid if it exists
	const href = uuid ? `/domain-analytics/details/${uuid}/` : null;

	const toggleExpansion = () => {
		expanded = _expansionState[name] = !expanded;
	};

	$: arrowDown = expanded;
</script>

<ul>
	<li>
		{#if children}
			<div class="node-container">
				<span class="arrow-container" on:click={toggleExpansion}>
					<span class="arrow" class:arrowDown>&#x25b6;</span>
				</span>
				{#if uuid}
					<a {href} class="label-text">{name}</a>
				{:else}
					<span class="label-text">{name}</span>
				{/if}
			</div>
			{#if expanded}
				{#each children as child}
					<svelte:self tree={child} />
				{/each}
			{/if}
		{:else}
			<div class="node-container">
				<span class="no-arrow"></span>
				{#if uuid}
					<a {href} class="label-text">{name}</a>
				{:else}
					<span class="label-text">{name}</span>
				{/if}
			</div>
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

	.node-container {
		display: flex;
		align-items: center;
	}

	.arrow-container {
		cursor: pointer;
		padding: 2px 4px;
	}

	.no-arrow {
		padding-left: 1rem;
	}

	.arrow {
		display: inline-block;
	}

	.arrowDown {
		transform: rotate(90deg);
	}

	.label-text {
		margin-left: 4px;
		cursor: pointer;
	}

	a.label-text {
		text-decoration: none;
		color: #0066cc;
	}

	a.label-text:hover {
		text-decoration: underline;
	}
</style>
