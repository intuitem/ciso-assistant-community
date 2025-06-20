<script lang="ts">
	import { setContext } from 'svelte';

	interface Props {
		/** Enable tree-view selection. */
		selection?: boolean;
		/** Enable selection of multiple items. */
		multiple?: boolean;
		/** Provide classes to set the tree width. */
		width?: string;
		/** Provide classes to set the vertical spacing between items. */
		spacing?: string;
		/** Set open by default on load. */
		open?: boolean;
		/** Set the tree disabled state */
		disabled?: boolean;
		/** Provide classes to set the tree item padding styles. */
		padding?: string;
		/** Provide classes to set the tree children indentation */
		indent?: string;
		/** Provide classes to set the tree item hover styles. */
		hover?: string;
		/** Provide classes to set the tree item rounded styles. */
		rounded?: string;
		/** Set the rotation of the item caret in the open state. */
		caretOpen?: string;
		/** Set the rotation of the item caret in the closed state. */
		caretClosed?: string;
		/* Set the hyphen symbol opacity for non-expandable rows. */
		hyphenOpacity?: string;
		/** Provide arbitrary classes to the tree item summary region. */
		regionSummary?: string;
		/** Provide arbitrary classes to the symbol icon region. */
		regionSymbol?: string;
		/** Provide arbitrary classes to the children region. */
		regionChildren?: string;
		/** Provide the ARIA labelledby value. */
		labelledby?: string;
		children?: import('svelte').Snippet;
	}

	let {
		selection = false,
		multiple = false,
		width = 'w-full',
		spacing = 'space-y-1',
		open = false,
		disabled = false,
		padding = 'py-4 px-4',
		indent = 'ml-4',
		hover = 'hover:preset-tonal',
		rounded = 'rounded-container-token',
		caretOpen = 'rotate-180',
		caretClosed = '',
		hyphenOpacity = 'opacity-10',
		regionSummary = '',
		regionSymbol = '',
		regionChildren = '',
		labelledby = '',
		children
	}: Props = $props();

	// Functionality
	/**
	 * expands all tree view items.
	 * @type {() => void}
	 */
	export function expandAll(): void {
		const detailsElements = tree.querySelectorAll<HTMLDetailsElement>('details.tree-item');
		detailsElements.forEach((details) => {
			if (!details.open) {
				const summary = details.querySelector<HTMLElement>('summary.tree-item-summary');
				if (summary) summary.click();
			}
		});
	}
	/**
	 * collapses all tree view items.
	 * @type {() => void}
	 */
	export function collapseAll(): void {
		const detailsElements = tree.querySelectorAll<HTMLDetailsElement>('details.tree-item');
		detailsElements.forEach((details) => {
			if (details.open) {
				const summary = details.querySelector<HTMLElement>('summary.tree-item-summary');
				if (summary) summary.click();
			}
		});
	}

	// Context API
	setContext('open', open);
	setContext('selection', selection);
	setContext('multiple', multiple);
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

	// Reactive
	let classesBase = $derived(`${width} ${spacing} `);

	// Locals
	let tree: HTMLDivElement = $state();
</script>

<div
	bind:this={tree}
	class="tree {classesBase}"
	data-testid="tree"
	role="tree"
	aria-multiselectable={multiple}
	aria-label={labelledby}
	aria-disabled={disabled}
>
	{@render children?.()}
</div>
