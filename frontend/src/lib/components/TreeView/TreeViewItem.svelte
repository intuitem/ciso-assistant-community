<svelte:options />

<script lang="ts">
	import TreeViewItem from './TreeViewItem.svelte';

	import { run } from 'svelte/legacy';

	import { createEventDispatcher, getContext, mount } from 'svelte';
	import RecursiveTreeViewItem from './RecursiveTreeViewItem.svelte';

	interface Props {
		// Props (state)
		group?: unknown;
		name?: string | undefined;
		value?: unknown;
		checked?: boolean;
		childrenProp?: any;
		mappingInference?: unknown;
		// Props (styles)
		spacing?: string;
		// Context API
		open?: boolean;
		selection?: boolean;
		multiple?: boolean;
		disabled?: boolean;
		indeterminate?: boolean;
		padding?: string;
		indent?: string;
		hover?: string;
		rounded?: string;
		caretOpen?: string;
		caretClosed?: string;
		hyphenOpacity?: string;
		regionSummary?: string;
		regionSymbol?: string;
		regionChildren?: string;
		// Props (work-around)
		alwaysDisplayCaret?: boolean;
		hideLead?: boolean;
		hideChildren?: boolean;
		classProp?: string; // Replacing $$props.class
		onToggle?: (isOpened: boolean) => void;
		children?: import('svelte').Snippet;
		lead?: import('svelte').Snippet;
		childrenSlot?: import('svelte').Snippet;
	}

	let {
		group = $bindable(undefined),
		name = $bindable(undefined),
		value = $bindable(undefined),
		checked = $bindable(false),
		childrenProp = $bindable(),
		mappingInference = undefined,
		spacing = 'space-x-4',
		open = $bindable(getContext('open')),
		selection = getContext('selection'),
		multiple = getContext('multiple'),
		disabled = getContext('disabled'),
		indeterminate = $bindable(false),
		padding = getContext('padding'),
		indent = getContext('indent'),
		hover = getContext('hover'),
		rounded = getContext('rounded-sm'),
		caretOpen = getContext('caretOpen'),
		caretClosed = getContext('caretClosed'),
		hyphenOpacity = getContext('hyphenOpacity'),
		regionSummary = getContext('regionSummary'),
		regionSymbol = getContext('regionSymbol'),
		regionChildren = getContext('regionChildren'),
		alwaysDisplayCaret = false,
		hideLead = false,
		hideChildren = false,
		onToggle = () => {},
		children,
		classProp = '',
		lead,
		childrenSlot
	}: Props = $props();

	// Locals
	let treeItem: HTMLDetailsElement = $state();
	let childrenDiv: HTMLDivElement = $state();

	const cBase = 'space-y-1';
	const cSummary = 'list-none [&::-webkit-details-marker]:hidden items-center cursor-pointer flex';
	const cSymbol = 'fill-current w-3 text-center transition-transform duration-200';
	const cChildren = 'space-y-1';
	const cDisabled = 'opacity-50 cursor-not-allowed!';

	let classesCaretState = $derived(
		open && ((childrenProp && !hideChildren) || alwaysDisplayCaret) ? caretOpen : caretClosed
	);
	let classesDisabled = $derived(disabled ? cDisabled : '');
	let classesBase = $derived(`${cBase} ${classProp}`);
	let classesSummary = $derived(
		`${cSummary} ${classesDisabled} ${spacing} ${rounded} ${padding} ${hover} ${regionSummary}`
	);
	let classesCaret = $derived(`${classesCaretState}`);
	let classesSymbol = $derived(`${cSymbol} ${classesCaret} ${regionSymbol}`);
	let classesHyphen = $derived(`${hyphenOpacity}`);
	let classesChildren = $derived(`${cChildren} ${indent} ${regionChildren}`);

	// Functionality
	function onSummaryClick(event: MouseEvent) {
		if (disabled) event.preventDefault();
	}

	function updateCheckbox(group: unknown, indeterminate: boolean) {
		if (!Array.isArray(group)) return;
		checked = group.indexOf(value) >= 0;
		dispatch('groupChange', { checked, indeterminate });
		dispatch('childChange');
	}
	function updateGroup(checked: boolean, indeterminate: boolean) {
		if (!Array.isArray(group)) return;
		const index = group.indexOf(value);
		if (checked) {
			if (index < 0) {
				group.push(value);
				group = group;
			}
		} else {
			if (index >= 0) {
				group.splice(index, 1);
				group = group;
			}
		}
		if (!indeterminate) onParentChange();
	}

	function updateRadio(group: unknown) {
		checked = group === value;
		dispatch('groupChange', { checked, indeterminate: false });
		if (group) dispatch('childChange');
	}
	function updateRadioGroup(checked: boolean) {
		if (checked && group !== value) group = value;
		else if (!checked && group === value) group = '';
	}

	function onChildValueChange() {
		if (multiple) {
			if (!Array.isArray(group)) return;
			const childrenValues = childrenProp.map((c) => c.value);
			const childrenGroup = childrenProp ? childrenProp[0].group : '';
			const index = group.indexOf(value);
			if (childrenProp.some((c) => c.indeterminate)) {
				indeterminate = true;
				if (index >= 0) {
					group.splice(index, 1);
					group = group;
				}
			} else if (
				childrenValues.every((c) => Array.isArray(childrenGroup) && childrenGroup.includes(c))
			) {
				indeterminate = false;
				if (index < 0) {
					group.push(value);
					group = group;
				}
			} else if (
				childrenValues.some((c) => Array.isArray(childrenGroup) && childrenGroup.includes(c))
			) {
				indeterminate = true;
				if (index >= 0) {
					group.splice(index, 1);
					group = group;
				}
			} else {
				indeterminate = false;
				if (index >= 0) {
					group.splice(index, 1);
					group = group;
				}
			}
		} else {
			if (group !== value && childrenProp.some((c) => c.checked)) {
				group = value;
			} else if (group === value && !childrenProp.some((c) => c.checked)) {
				group = '';
			}
		}
		dispatch('childChange');
	}

	export function onParentChange() {
		if (!multiple || !childrenProp || childrenProp.length === 0) return;
		if (!Array.isArray(group)) return;
		const index = group.indexOf(value);

		const checkChild = (child: TreeViewItem) => {
			if (!child || !Array.isArray(child.group)) return;
			child.indeterminate = false;
			if (child.group.indexOf(child.value) < 0) {
				child.group.push(child.value);
			}
		};
		const uncheckChild = (child: TreeViewItem) => {
			if (!child || !Array.isArray(child.group)) return;
			child.indeterminate = false;
			const childIndex = child.group.indexOf(child.value);
			if (childIndex >= 0) {
				child.group.splice(childIndex, 1);
			}
		};

		childrenProp.forEach((child) => {
			if (!child) return;
			index >= 0 ? checkChild(child) : uncheckChild(child);
			child.onParentChange();
		});
	}

	const dispatch = createEventDispatcher();

	function onKeyDown(event: KeyboardEvent | HTMLDivElement): void {
		function getRootTree(): HTMLDivElement | undefined {
			let currentElement: HTMLElement | null = treeItem;
			while (currentElement !== null) {
				if (currentElement.classList.contains('tree')) return currentElement as HTMLDivElement;
				currentElement = currentElement.parentElement;
			}
			return undefined;
		}

		let rootTree: HTMLDivElement | undefined = undefined;
		let lastVisibleElement: HTMLElement | undefined | null = null;

		switch (event.code) {
			case 'ArrowRight':
				if (!open) open = true;
				else if (children && !hideChildren) {
					const child = childrenDiv.querySelector<HTMLElement>('details>summary');
					if (child) child.focus();
				}
				break;
			case 'ArrowLeft':
				if (open) open = false;
				else {
					const parent = treeItem.parentElement?.parentElement;
					if (parent && parent.tagName === 'DETAILS')
						parent.querySelector<HTMLElement>('summary')?.focus();
				}
				break;
			case 'Home':
				event.preventDefault();
				rootTree = getRootTree();
				if (rootTree) rootTree?.querySelector('summary')?.focus();
				break;
			case 'End':
				event.preventDefault();
				rootTree = getRootTree();
				if (rootTree) {
					const detailsElements = rootTree?.querySelectorAll('details');
					if (!detailsElements) return;
					for (let i = detailsElements.length - 1; i >= 0; i--) {
						const details = detailsElements[i];
						if (
							details.parentElement?.classList?.contains('tree') ||
							details.parentElement?.parentElement?.getAttribute('open') !== null
						) {
							lastVisibleElement = details;
							break;
						} else if (details.parentElement?.parentElement?.tagName !== 'details') {
							lastVisibleElement = details.parentElement.parentElement;
							break;
						}
					}
					if (lastVisibleElement) {
						const summary = lastVisibleElement.querySelector('summary');
						if (summary) summary.focus();
					}
				}
				break;
		}
	}

	run(() => {
		if (multiple) updateCheckbox(group, indeterminate);
	});
	run(() => {
		if (multiple) updateGroup(checked, indeterminate);
	});
	run(() => {
		if (!multiple) updateRadio(group);
	});
	run(() => {
		if (!multiple) updateRadioGroup(checked);
	});
	run(() => {
		if (!multiple && group !== undefined && childrenProp) {
			if (group !== value) {
				childrenProp.forEach((child) => {
					if (child) child.group = '';
				});
			}
		}
	});

	$effect(() => onToggle(open));
	run(() => {
		childrenProp?.forEach((child) => {
			if (child)
				mount(RecursiveTreeViewItem, {
					target: treeItem,
					events: { childChange: () => onChildValueChange() }
				});
		});
	});

	export {
		mappingInference,
		spacing,
		multiple,
		disabled,
		padding,
		indent,
		hover,
		rounded,
		caretOpen,
		caretClosed,
		hyphenOpacity,
		regionSummary,
		regionSymbol,
		regionChildren,
		hideLead,
		hideChildren,
		classProp
	};
</script>

<details
	bind:this={treeItem}
	bind:open
	class="tree-item {classesBase}"
	data-testid="tree-item"
	aria-disabled={disabled}
>
	<summary
		class="tree-item-summary {classesSummary}"
		role="treeitem"
		aria-selected={selection ? checked : undefined}
		aria-expanded={childrenProp ? open : undefined}
		onclick={onSummaryClick}
		onkeydown={onKeyDown}
	>
		<!-- Symbol -->
		<div class="tree-summary-symbol {classesSymbol}">
			{#if (childrenProp && !hideChildren) || alwaysDisplayCaret}
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
					<path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/>
				</svg>
			{:else}
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" class="w-3 {classesHyphen}">
					<path
						d="M432 256c0 17.7-14.3 32-32 32L48 288c-17.7 0-32-14.3-32-32s14.3-32 32-32l352 0c17.7 0 32 14.3 32 32z"
					/>
				</svg>
			{/if}
		</div>

		<!-- Selection -->
		{#if selection && name && group !== undefined}
			{#if multiple}
				<input
					class="checkbox tree-item-checkbox"
					type="checkbox"
					{name}
					{value}
					bind:checked
					bind:indeterminate
					onchange={onParentChange}
				/>
			{:else}
				<input class="radio tree-item-radio" type="radio" bind:group {name} {value} />
			{/if}
		{/if}

		<!-- Slot: Content -->
		<div class="tree-item-content w-full" data-testid="tree-item-content">
			{@render children?.()}
		</div>

		<!-- Slot: Lead -->
		{#if lead && !hideLead}
			<div class="tree-item-lead flex flex-row items-center space-x-2" data-testid="tree-item-lead">
				{#if mappingInference}
					<i class="fa-solid fa-diagram-project"></i>
				{/if}
				{@render lead?.()}
			</div>
		{/if}
	</summary>

	<div bind:this={childrenDiv} class="tree-item-children {classesChildren}" role="group">
		{@render childrenSlot?.()}
	</div>
</details>
