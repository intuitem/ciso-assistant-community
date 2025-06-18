<script lang="ts">
	import { createEventDispatcher, onMount, setContext } from 'svelte';

	import RecursiveTreeViewItem from '$lib/components/TreeView/RecursiveTreeViewItem.svelte';
	import type { TreeViewNode } from './types';

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
		width?: string;
		spacing?: string;
		// Props (children)
		open?: boolean;
		disabled?: boolean;
		padding?: string;
		indent?: string;
		hover?: string;
		rounded?: string;
		// Props (symbols)
		caretOpen?: string;
		caretClosed?: string;
		hyphenOpacity?: string;
		// Props (regions)
		regionSummary?: string;
		regionSymbol?: string;
		regionChildren?: string;
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
		hover = 'hover:preset-tonal',
		rounded = 'rounded-container',
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
	setContext('rounded-sm', rounded);
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
