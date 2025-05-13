<script lang="ts">
	import { createEventDispatcher, onMount, setContext } from 'svelte';

	// Types
	import RecursiveTreeViewItem from '$lib/components/TreeView/RecursiveTreeViewItem.svelte';
	import type { CssClasses, TreeViewNode } from '@skeletonlabs/skeleton';

	

	

	

	

	
	interface Props {
		// Props (parent)
		selection?: boolean;
		multiple?: boolean;
		relational?: boolean;
		nodes?: TreeViewNode[];
		expandedNodes?: string[];
		disabledNodes?: string[];
		checkedNodes?: string[];
		indeterminateNodes?: string[];
		width?: CssClasses;
		spacing?: CssClasses;
		// Props (children)
		open?: boolean;
		disabled?: boolean;
		padding?: CssClasses;
		indent?: CssClasses;
		hover?: CssClasses;
		rounded?: CssClasses;
		// Props (symbols)
		caretOpen?: CssClasses;
		caretClosed?: CssClasses;
		hyphenOpacity?: CssClasses;
		// Props (regions)
		regionSummary?: CssClasses;
		regionSymbol?: CssClasses;
		regionChildren?: CssClasses;
		// Props A11y
		labelledby?: string;
	}

	let {
		selection = false,
		multiple = false,
		relational = false,
		nodes = [],
		expandedNodes = $bindable([]),
		disabledNodes = $bindable([]),
		checkedNodes = $bindable([]),
		indeterminateNodes = $bindable([]),
		width = 'w-full',
		spacing = 'space-y-1',
		open = false,
		disabled = false,
		padding = 'py-4 px-4',
		indent = 'ml-4',
		hover = 'hover:variant-soft',
		rounded = 'rounded-container-token',
		caretOpen = '',
		caretClosed = '-rotate-90',
		hyphenOpacity = 'opacity-10',
		regionSummary = '',
		regionSymbol = '',
		regionChildren = '',
		labelledby = ''
	}: Props = $props();

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
	let classesBase = $derived(`${width} ${spacing} ${classProp}`);

	let mounted = $state(false);
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
