<script lang="ts">
	import { createEventDispatcher, onMount, setContext } from 'svelte';

	// Types
	import RecursiveTreeViewItem from '$lib/components/TreeView/RecursiveTreeViewItem.svelte';
	import type { CssClasses, TreeViewNode } from '@skeletonlabs/skeleton';

	// Props (parent)
	export let selection = false;
	export let multiple = false;
	export let relational = false;
	export let nodes: TreeViewNode[] = [];
	export let expandedNodes: string[] = [];
	export let disabledNodes: string[] = [];
	export let checkedNodes: string[] = [];
	export let indeterminateNodes: string[] = [];
	export let width: CssClasses = 'w-full';
	export let spacing: CssClasses = 'space-y-1';

	// Props (children)
	export let open = false;
	export let disabled = false;
	export let padding: CssClasses = 'py-4 px-4';
	export let indent: CssClasses = 'ml-4';
	export let hover: CssClasses = 'hover:variant-soft';
	export let rounded: CssClasses = 'rounded-container-token';

	// Props (symbols)
	export let caretOpen: CssClasses = '';
	export let caretClosed: CssClasses = '-rotate-90';
	export let hyphenOpacity: CssClasses = 'opacity-10';

	// Props (regions)
	export let regionSummary: CssClasses = '';
	export let regionSymbol: CssClasses = '';
	export let regionChildren: CssClasses = '';

	// Props A11y
	export let labelledby = '';

	// Context API
	setContext('open', open);
	setContext('selection', selection);
	setContext('multiple', multiple);
	setContext('relational', relational);
	setContext('disabled', disabled);
	setContext('padding', padding);
	setContext('indent', indent);
	setContext('hover', hover);
	setContext('rounded', rounded);
	setContext('caretOpen', caretOpen);
	setContext('caretClosed', caretClosed);
	setContext('hyphenOpacity', hyphenOpacity);
	setContext('regionSummary', regionSummary);
	setContext('regionSymbol', regionSymbol);
	setContext('regionChildren', regionChildren);

	// events
	const dispatch = createEventDispatcher();

	function onClick(event: CustomEvent<{ id: string }>) {
		dispatch('click', { id: event.detail.id });
	}

	function onToggle(event: CustomEvent<{ id: string }>) {
		dispatch('toggle', { id: event.detail.id });
	}

	// Reactive
	let classProp = ''; // Replacing $$props.class
	$: classesBase = `${width} ${spacing} ${classProp}`;

	let mounted = false;
	onMount(() => {
		mounted = true;
	});
</script>

<div
	class="tree {classesBase}"
	data-testid="tree"
	role="tree"
	aria-multiselectable={multiple}
	aria-label={labelledby}
	aria-disabled={disabled}
>
	{#if mounted && nodes && nodes.length > 0}
		<RecursiveTreeViewItem
			{nodes}
			bind:expandedNodes
			bind:disabledNodes
			bind:checkedNodes
			bind:indeterminateNodes
			on:click={onClick}
			on:toggle={onToggle}
		/>
	{:else}
		<div class="placeholder animate-pulse"></div>
	{/if}
</div>
