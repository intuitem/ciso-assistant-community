<svelte:options accessors />

<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';

	// Types
	import type { CssClasses, SvelteEvent, TreeViewItem } from '@skeletonlabs/skeleton';

	// Props (state)
	export let group: unknown = undefined;
	export let name: string | undefined = undefined;
	export let value: unknown = undefined;
	export let checked = false;
	export let children: TreeViewItem[] = [];
	export let mappingInference: unknown = undefined;

	// Props (styles)
	export let spacing: CssClasses = 'space-x-4';

	// Context API
	export let open: boolean = getContext('open');
	export let selection: boolean = getContext('selection');
	export let multiple: boolean = getContext('multiple');
	export let disabled: boolean = getContext('disabled');
	export let indeterminate = false;
	export let padding: CssClasses = getContext('padding');
	export let indent: CssClasses = getContext('indent');
	export let hover: CssClasses = getContext('hover');
	export let rounded: CssClasses = getContext('rounded');
	export let caretOpen: CssClasses = getContext('caretOpen');
	export let caretClosed: CssClasses = getContext('caretClosed');
	export let hyphenOpacity: CssClasses = getContext('hyphenOpacity');
	export let regionSummary: CssClasses = getContext('regionSummary');
	export let regionSymbol: CssClasses = getContext('regionSymbol');
	export let regionChildren: CssClasses = getContext('regionChildren');

	// Props (work-around)
	export let hideLead = false;
	export let hideChildren = false;

	// Locals
	let treeItem: HTMLDetailsElement;
	let childrenDiv: HTMLDivElement;

	// Functionality
	function onSummaryClick(event: MouseEvent) {
		if (disabled) event.preventDefault();
	}

	$: if (multiple) updateCheckbox(group, indeterminate);
	$: if (multiple) updateGroup(checked, indeterminate);
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

	$: if (!multiple) updateRadio(group);
	$: if (!multiple) updateRadioGroup(checked);
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
			const childrenValues = children.map((c) => c.value);
			const childrenGroup = children[0].group;
			const index = group.indexOf(value);
			if (children.some((c) => c.indeterminate)) {
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
			if (group !== value && children.some((c) => c.checked)) {
				group = value;
			} else if (group === value && !children.some((c) => c.checked)) {
				group = '';
			}
		}
		dispatch('childChange');
	}

	export function onParentChange() {
		if (!multiple || !children || children.length === 0) return;
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

		children.forEach((child) => {
			if (!child) return;
			index >= 0 ? checkChild(child) : uncheckChild(child);
			child.onParentChange();
		});
	}

	$: if (!multiple && group !== undefined) {
		if (group !== value) {
			children.forEach((child) => {
				if (child) child.group = '';
			});
		}
	}

	const dispatch = createEventDispatcher();
	$: dispatch('toggle', { open });

	$: children.forEach((child) => {
		if (child) child.$on('childChange', onChildValueChange);
	});

	function onKeyDown(event: SvelteEvent<KeyboardEvent, HTMLDivElement>): void {
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
				else if ($$slots.children && !hideChildren) {
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

	const cBase = 'space-y-1';
	const cSummary = 'list-none [&::-webkit-details-marker]:hidden items-center cursor-pointer flex';
	const cSymbol = 'fill-current w-3 text-center transition-transform duration-[200ms]';
	const cChildren = 'space-y-1';
	const cDisabled = 'opacity-50 !cursor-not-allowed';

	$: classesCaretState = open && $$slots.children && !hideChildren ? caretOpen : caretClosed;
	$: classesDisabled = disabled ? cDisabled : '';
	export let classProp = ''; // Replacing $$props.class
	$: classesBase = `${cBase} ${classProp}`;
	$: classesSummary = `${cSummary} ${classesDisabled} ${spacing} ${rounded} ${padding} ${hover} ${regionSummary}`;
	$: classesSymbol = `${cSymbol} ${classesCaret} ${regionSymbol}`;
	$: classesCaret = `${classesCaretState}`;
	$: classesHyphen = `${hyphenOpacity}`;
	$: classesChildren = `${cChildren} ${indent} ${regionChildren}`;
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
		aria-expanded={$$slots.children ? open : undefined}
		on:click={onSummaryClick}
		on:keydown={onKeyDown}
	>
		<!-- Symbol -->
		<div class="tree-summary-symbol {classesSymbol}">
			{#if $$slots.children && !hideChildren}
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
					on:change={onParentChange}
				/>
			{:else}
				<input class="radio tree-item-radio" type="radio" bind:group {name} {value} />
			{/if}
		{/if}

		<!-- Slot: Content -->
		<div class="tree-item-content w-full" data-testid="tree-item-content">
			<slot />
		</div>

		<!-- Slot: Lead -->
		{#if $$slots.lead && !hideLead}
			<div class="tree-item-lead flex flex-row items-center space-x-2" data-testid="tree-item-lead">
				{#if mappingInference}
					<i class="fa-solid fa-diagram-project" />
				{/if}
				<slot name="lead" />
			</div>
		{/if}
	</summary>

	<div bind:this={childrenDiv} class="tree-item-children {classesChildren}" role="group">
		<slot name="children" />
	</div>
</details>
