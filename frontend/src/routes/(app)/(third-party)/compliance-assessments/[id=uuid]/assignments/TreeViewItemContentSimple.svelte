<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';

	interface Props {
		name: string;
		urn: string;
		node_content: string;
		assessable: boolean;
		hasParentNode: boolean;
		assignmentInfo: { assignmentName: string; actorName: string } | null;
		isAssigned: boolean;
		nodeId: string;
		childrenIds: string[]; // IDs of all assessable children (for batch selection)
	}

	let {
		name,
		urn,
		node_content,
		assessable,
		hasParentNode,
		assignmentInfo,
		isAssigned,
		nodeId,
		childrenIds = []
	}: Props = $props();

	// Get the checked nodes set and assigned nodes set from context
	const checkedNodesStore = getContext<Writable<Set<string>>>('checkedNodes');
	const assignedNodesStore = getContext<Writable<Set<string>>>('assignedNodes');

	// For leaf nodes: check if this node is checked
	let isChecked = $derived($checkedNodesStore?.has(nodeId) ?? false);

	// For parent nodes: calculate selection state of children
	let availableChildrenIds = $derived(
		childrenIds.filter(id => !$assignedNodesStore?.has(id))
	);

	let checkedChildrenCount = $derived(
		availableChildrenIds.filter(id => $checkedNodesStore?.has(id)).length
	);

	let allChildrenChecked = $derived(
		availableChildrenIds.length > 0 && checkedChildrenCount === availableChildrenIds.length
	);

	let someChildrenChecked = $derived(
		checkedChildrenCount > 0 && checkedChildrenCount < availableChildrenIds.length
	);

	// Handle checkbox change for leaf nodes
	function handleLeafCheckboxChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if ($checkedNodesStore) {
			const newSet = new Set($checkedNodesStore);
			if (target.checked) {
				newSet.add(nodeId);
			} else {
				newSet.delete(nodeId);
			}
			$checkedNodesStore = newSet;
		}
	}

	// Handle checkbox change for parent nodes (batch select/deselect children)
	function handleParentCheckboxChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if ($checkedNodesStore) {
			const newSet = new Set($checkedNodesStore);
			if (target.checked) {
				// Select all available children
				for (const childId of availableChildrenIds) {
					newSet.add(childId);
				}
			} else {
				// Deselect all children
				for (const childId of availableChildrenIds) {
					newSet.delete(childId);
				}
			}
			$checkedNodesStore = newSet;
		}
	}
</script>

<!-- Row container with status-based background -->
<div
	class="flex items-center gap-3 py-1.5 px-2 rounded-md transition-colors -ml-2
		{assessable
			? isAssigned
				? 'bg-gray-100 border border-gray-200'
				: isChecked
					? 'bg-violet-50 border border-violet-200'
					: 'bg-green-50 border border-green-200 hover:bg-green-100 cursor-pointer'
			: ''}"
	class:pl-2={hasParentNode}
	onclick={(e) => {
		// Allow clicking the row to toggle checkbox for available assessable nodes
		if (assessable && !isAssigned) {
			const target = e.target as HTMLElement;
			// Don't toggle if clicking directly on the checkbox
			if (target.tagName !== 'INPUT') {
				if ($checkedNodesStore) {
					const newSet = new Set($checkedNodesStore);
					if (isChecked) {
						newSet.delete(nodeId);
					} else {
						newSet.add(nodeId);
					}
					$checkedNodesStore = newSet;
				}
			}
		}
	}}
>
	<!-- Checkbox -->
	{#if assessable}
		<!-- Leaf node checkbox -->
		<input
			type="checkbox"
			class="checkbox checkbox-sm {isAssigned ? '' : 'border-green-500 checked:bg-violet-500'}"
			checked={isChecked}
			disabled={isAssigned}
			onchange={handleLeafCheckboxChange}
			onclick={(e) => e.stopPropagation()}
		/>
	{:else if childrenIds.length > 0}
		<!-- Parent node checkbox for batch selection -->
		<input
			type="checkbox"
			class="checkbox checkbox-sm"
			checked={allChildrenChecked}
			indeterminate={someChildrenChecked}
			disabled={availableChildrenIds.length === 0}
			onchange={handleParentCheckboxChange}
			onclick={(e) => e.stopPropagation()}
		/>
	{/if}

	<div class="flex flex-col flex-1">
		<div class="flex items-center gap-2">
			<!-- Status icon for assessable nodes -->
			{#if assessable}
				{#if isAssigned}
					<span class="text-gray-400" title="Already assigned">
						<i class="fa-solid fa-lock text-xs"></i>
					</span>
				{/if}
			{/if}

			<!-- Ref ID / Name -->
			<span class="font-medium text-sm {assessable ? (isAssigned ? 'text-gray-500' : 'text-gray-900') : 'text-gray-600'}">
				{#if node_content}
					{node_content}
				{:else}
					{name}
				{/if}
			</span>

			<!-- Assignment badge -->
			{#if assignmentInfo}
				<span
					class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700 border border-blue-200"
					title="Assigned to {assignmentInfo.actorName} ({assignmentInfo.assignmentName})"
				>
					<i class="fa-solid fa-user text-xs"></i>
					<span class="max-w-[100px] truncate">{assignmentInfo.actorName}</span>
				</span>
			{/if}

			<!-- Children count for parent nodes -->
			{#if !assessable && childrenIds.length > 0}
				<span class="text-xs text-gray-400">
					({availableChildrenIds.length} {safeTranslate('available')})
				</span>
			{/if}
		</div>

		<!-- Non-assessable indicator -->
		{#if !assessable && childrenIds.length === 0}
			<span class="text-xs text-gray-400 italic">
				({safeTranslate('section')})
			</span>
		{/if}
	</div>
</div>
