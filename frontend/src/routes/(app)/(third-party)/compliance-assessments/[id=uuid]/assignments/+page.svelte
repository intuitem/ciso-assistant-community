<script lang="ts">
	import { page } from '$app/state';
	import { invalidateAll } from '$app/navigation';
	import { applyAction, deserialize } from '$app/forms';
	import { setContext } from 'svelte';
	import { writable } from 'svelte/store';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import type { TreeViewNode } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import TreeViewItemContentSimple from './TreeViewItemContentSimple.svelte';
	import TreeViewItemLeadSimple from './TreeViewItemLeadSimple.svelte';
	import { complianceResultColorMap } from '$lib/utils/constants';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { getToastStore } from '$lib/components/Toast/stores';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const toastStore = getToastStore();

	// Create superForm instance for AutocompleteSelect - keep full result
	const assignmentSuperForm = superForm(data.assignmentForm, {
		dataType: 'json'
	});
	const { form: assignmentFormStore } = assignmentSuperForm;

	// Create writable stores for checked nodes and assigned nodes, provide via context
	const checkedNodesStore = writable<Set<string>>(new Set());
	setContext('checkedNodes', checkedNodesStore);

	// Edit mode: track which assignment is being edited
	let editingAssignmentId = $state<string | null>(null);

	// Store for editing requirement IDs (nodes belonging to the assignment being edited)
	const editingRequirementIdsStore = writable<Set<string>>(new Set());
	setContext('editingRequirementIds', editingRequirementIdsStore);

	// Assignments from server data
	let assignments = $derived(data.assignments);

	// Track which requirement IDs are already assigned (excluding the one being edited)
	let assignedRequirementIds = $derived(
		new Set(
			assignments
				.filter((a) => a.id !== editingAssignmentId)
				.flatMap((assignment) => assignment.requirement_assessments)
		)
	);

	// Create a writable store for assigned nodes that updates when assignedRequirementIds changes
	const assignedNodesStore = writable<Set<string>>(new Set());
	setContext('assignedNodes', assignedNodesStore);

	// Keep the assigned nodes store in sync with the derived value
	$effect(() => {
		$assignedNodesStore = assignedRequirementIds;
	});

	// State for tree expansion
	let expandedNodes: string[] = $state([]);

	// State for assignment creation/update
	let isCreating = $state(false);
	let isUpdating = $state(false);
	let isDeleting = $state<string | null>(null);

	// State for requirements detail modal
	let showRequirementsModal = $state(false);
	let selectedAssignmentForModal = $state<(typeof assignments)[0] | null>(null);

	// Get selected actor IDs from form store (now an array)
	let selectedActorIds = $derived(($assignmentFormStore.actor as string[]) ?? []);
	let hasSelectedActors = $derived(selectedActorIds.length > 0);

	// Get assignment info for a node - returns array of actor names
	function getAssignmentInfo(nodeId: string): Array<{ actorName: string }> | null {
		for (const assignment of assignments) {
			if (assignment.requirement_assessments.includes(nodeId)) {
				return assignment.actor.map((a: { str: string }) => ({ actorName: a.str }));
			}
		}
		return null;
	}

	interface Node {
		name: string;
		urn: string;
		parent_urn?: string;
		node_content: string;
		assessable: boolean;
		style: string;
		children?: Record<string, Node>;
		status?: string;
		result?: string;
		ra_id?: string;
	}

	// Build a lookup map from requirement assessment ID to node details
	function buildRequirementLookup(
		nodes: Record<string, Node>
	): Map<string, { node_content: string; name: string; result?: string }> {
		const lookup = new Map<string, { node_content: string; name: string; result?: string }>();

		function traverse(node: Node) {
			if (node.ra_id) {
				lookup.set(node.ra_id, {
					node_content: node.node_content,
					name: node.name,
					result: node.result
				});
			}
			if (node.children) {
				for (const childNode of Object.values(node.children)) {
					traverse(childNode);
				}
			}
		}

		for (const node of Object.values(nodes)) {
			traverse(node);
		}

		return lookup;
	}

	let requirementLookup = $derived(buildRequirementLookup(data.tree));

	// Get requirement details for an assignment
	function getRequirementDetails(
		requirementIds: string[]
	): Array<{ id: string; node_content: string; name: string; result?: string }> {
		return requirementIds
			.map((id) => {
				const details = requirementLookup.get(id);
				return {
					id,
					node_content: details?.node_content ?? '',
					name: details?.name ?? 'Unknown',
					result: details?.result
				};
			})
			.sort((a, b) => a.node_content.localeCompare(b.node_content));
	}

	// Open the requirements modal for an assignment
	function openRequirementsModal(assignment: (typeof assignments)[0]) {
		selectedAssignmentForModal = assignment;
		showRequirementsModal = true;
	}

	// Close the requirements modal
	function closeRequirementsModal() {
		showRequirementsModal = false;
		selectedAssignmentForModal = null;
	}

	// Get unique actor assignments for all assessable descendants of a section node
	function getSectionAssignments(node: Node): Array<{ actorName: string }> {
		const actorNames = new Set<string>();
		const descendantIds = getAssessableDescendantIds(node);
		for (const raId of descendantIds) {
			const infos = getAssignmentInfo(raId);
			if (infos) {
				for (const info of infos) {
					actorNames.add(info.actorName);
				}
			}
		}
		return [...actorNames].map((name) => ({ actorName: name }));
	}

	// Helper function to get all assessable descendant IDs from a node
	function getAssessableDescendantIds(node: Node): string[] {
		const ids: string[] = [];

		// If this node is assessable and has an ra_id, include it
		if (node.assessable && node.ra_id) {
			ids.push(node.ra_id);
		}

		// Recursively get IDs from children
		if (node.children) {
			for (const [_, childNode] of Object.entries(node.children)) {
				ids.push(...getAssessableDescendantIds(childNode));
			}
		}

		return ids;
	}

	function transformToTreeView(
		nodes: [string, Node][],
		hasParentNode: boolean = false
	): TreeViewNode[] {
		return nodes.map(([id, node]) => {
			const nodeId = node.ra_id || id;
			const assignmentInfo = node.ra_id ? getAssignmentInfo(node.ra_id) : null;
			const isAssigned = node.ra_id ? assignedRequirementIds.has(node.ra_id) : false;

			// Get all assessable descendant IDs for batch selection
			const childrenIds = node.assessable ? [] : getAssessableDescendantIds(node);

			// For section nodes, get aggregated assignment info
			const sectionAssignments = node.assessable ? [] : getSectionAssignments(node);

			return {
				id: nodeId,
				content: TreeViewItemContentSimple,
				contentProps: {
					name: node.name,
					urn: node.urn,
					node_content: node.node_content,
					assessable: node.assessable,
					hasParentNode,
					assignmentInfo,
					isAssigned,
					nodeId: nodeId,
					childrenIds: childrenIds,
					sectionAssignments
				},
				lead: TreeViewItemLeadSimple,
				leadProps: {
					assessable: node.assessable,
					result: node.result,
					resultColor: complianceResultColorMap[node.result || 'not_assessed'],
					isAssigned,
					assignmentInfo
				},
				children: node.children ? transformToTreeView(Object.entries(node.children), true) : []
			};
		});
	}

	let treeViewNodes = $derived(transformToTreeView(Object.entries(data.tree)));

	// Get checked nodes as array, filtering out already assigned ones
	let availableCheckedNodes = $derived(
		[...$checkedNodesStore].filter((id) => !assignedRequirementIds.has(id))
	);

	// Get all assessable node IDs (for "select all" functionality)
	function getAllAssessableIds(nodes: TreeViewNode[]): string[] {
		const ids: string[] = [];
		for (const node of nodes) {
			if (node.contentProps?.assessable && !assignedRequirementIds.has(node.id)) {
				ids.push(node.id);
			}
			if (node.children) {
				ids.push(...getAllAssessableIds(node.children));
			}
		}
		return ids;
	}

	async function handleCreateAssignment() {
		if (!hasSelectedActors || availableCheckedNodes.length === 0) {
			return;
		}

		isCreating = true;
		try {
			const formData = new FormData();
			formData.append('actor', JSON.stringify(selectedActorIds));
			formData.append('requirement_assessments', JSON.stringify(availableCheckedNodes));
			formData.append('compliance_assessment', data.compliance_assessment.id);
			formData.append('folder', data.compliance_assessment.folder.id);

			const response = await fetch(`?/create`, {
				method: 'POST',
				body: formData
			});

			const result = deserialize(await response.text());
			if (result.type === 'success' && result.data?.status === 201) {
				// Reset form
				$assignmentFormStore.actor = [];
				$checkedNodesStore = new Set();
				// Apply the action result and refresh page data
				await applyAction(result);
				await invalidateAll();
				toastStore.trigger({
					message: m.assignmentCreated(),
					background: 'variant-filled-success',
					timeout: 3000
				});
			} else {
				console.error('Failed to create assignment:', result);
				toastStore.trigger({
					message: m.assignmentCreationFailed(),
					background: 'variant-filled-error',
					timeout: 3000
				});
			}
		} catch (error) {
			console.error('Error creating assignment:', error);
			toastStore.trigger({
				message: m.assignmentCreationFailed(),
				background: 'variant-filled-error',
				timeout: 3000
			});
		} finally {
			isCreating = false;
		}
	}

	async function handleDeleteAssignment(assignmentId: string) {
		isDeleting = assignmentId;
		try {
			const formData = new FormData();
			formData.append('id', assignmentId);

			const response = await fetch(`?/delete`, {
				method: 'POST',
				body: formData
			});

			const result = deserialize(await response.text());
			if (result.type === 'success' && result.data?.status === 204) {
				// Apply the action result and refresh page data
				await applyAction(result);
				await invalidateAll();
				toastStore.trigger({
					message: m.assignmentDeleted(),
					background: 'variant-filled-success',
					timeout: 3000
				});
			} else {
				console.error('Failed to delete assignment:', result);
				toastStore.trigger({
					message: m.assignmentDeletionFailed(),
					background: 'variant-filled-error',
					timeout: 3000
				});
			}
		} catch (error) {
			console.error('Error deleting assignment:', error);
			toastStore.trigger({
				message: m.assignmentDeletionFailed(),
				background: 'variant-filled-error',
				timeout: 3000
			});
		} finally {
			isDeleting = null;
		}
	}

	function startEdit(assignment: (typeof assignments)[0]) {
		editingAssignmentId = assignment.id;
		// Populate the form with the assignment's actors (array of IDs)
		$assignmentFormStore.actor = assignment.actor.map((a: { id: string }) => a.id);
		// Populate checked nodes with the assignment's requirements
		$checkedNodesStore = new Set(assignment.requirement_assessments);
		// Set the editing requirement IDs for tree styling
		$editingRequirementIdsStore = new Set(assignment.requirement_assessments);
	}

	function cancelEdit() {
		editingAssignmentId = null;
		$assignmentFormStore.actor = [];
		$checkedNodesStore = new Set();
		$editingRequirementIdsStore = new Set();
	}

	async function handleUpdateAssignment() {
		if (!editingAssignmentId || !hasSelectedActors || availableCheckedNodes.length === 0) {
			return;
		}

		isUpdating = true;
		try {
			const formData = new FormData();
			formData.append('id', editingAssignmentId);
			formData.append('actor', JSON.stringify(selectedActorIds));
			formData.append('requirement_assessments', JSON.stringify(availableCheckedNodes));

			const response = await fetch(`?/update`, {
				method: 'POST',
				body: formData
			});

			const result = deserialize(await response.text());
			if (result.type === 'success' && result.data?.status === 200) {
				// Reset edit state
				cancelEdit();
				await applyAction(result);
				await invalidateAll();
				toastStore.trigger({
					message: m.assignmentUpdated(),
					background: 'variant-filled-success',
					timeout: 3000
				});
			} else {
				console.error('Failed to update assignment:', result);
				toastStore.trigger({
					message: m.assignmentUpdateFailed(),
					background: 'variant-filled-error',
					timeout: 3000
				});
			}
		} catch (error) {
			console.error('Error updating assignment:', error);
			toastStore.trigger({
				message: m.assignmentUpdateFailed(),
				background: 'variant-filled-error',
				timeout: 3000
			});
		} finally {
			isUpdating = false;
		}
	}

	function handleSelectAll() {
		const allIds = getAllAssessableIds(treeViewNodes);
		$checkedNodesStore = new Set(allIds);
	}

	function handleClearSelection() {
		$checkedNodesStore = new Set();
	}

	function expandAll() {
		function getAllNodeIds(nodes: TreeViewNode[]): string[] {
			const ids: string[] = [];
			for (const node of nodes) {
				if (node.children && node.children.length > 0) {
					ids.push(node.id);
					ids.push(...getAllNodeIds(node.children));
				}
			}
			return ids;
		}
		expandedNodes = getAllNodeIds(treeViewNodes);
	}

	function collapseAll() {
		expandedNodes = [];
	}

	// Helper to format actor display string
	function formatActors(actors: Array<{ str: string; type?: string }>): string {
		return actors.map((a) => a.str).join(', ');
	}

	// Helper to determine icon for actor list
	function actorIcon(actors: Array<{ type?: string }>): string {
		if (actors.length > 1) return 'users';
		return actors[0]?.type === 'user' ? 'user' : 'users';
	}
</script>

<div class="flex flex-col space-y-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center space-x-4">
			<Anchor
				href="/compliance-assessments/{page.params.id}"
				class="btn preset-outlined-surface-500"
			>
				<i class="fa-solid fa-arrow-left mr-2"></i>
				{m.back()}
			</Anchor>
			<h1 class="h3 font-bold">{m.assignments()}</h1>
		</div>
	</div>

	<!-- Info banner -->
	<div class="alert bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
		<div class="flex items-start">
			<i class="fa-solid fa-info-circle text-blue-600 mr-3 mt-0.5"></i>
			<div class="text-sm">
				<p class="font-medium">{m.aboutAssignments()}</p>
				<p class="mt-1">
					{m.assignmentsDescription()}
				</p>
			</div>
		</div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
		<!-- Left Panel: Tree with Checkboxes -->
		<div class="lg:col-span-2 card bg-white shadow-lg p-4">
			<div class="flex items-center justify-between mb-4">
				<div>
					<h2 class="h4 font-semibold">{m.requirements()}</h2>
					<p class="text-sm text-gray-500">
						{m.selectRequirementsToAssign()}
					</p>
				</div>
				<div class="flex items-center space-x-2">
					<span class="badge bg-violet-100 text-violet-700 px-2 py-1 text-xs">
						{availableCheckedNodes.length}
						{m.selected()}
					</span>
				</div>
			</div>

			<!-- Tree controls -->
			<div class="flex flex-wrap items-center gap-2 mb-4 pb-4 border-b">
				<button class="btn btn-sm preset-outlined-primary-500" onclick={handleSelectAll}>
					<i class="fa-solid fa-check-double mr-1"></i>
					{m.selectAllAvailable()}
				</button>
				<button class="btn btn-sm preset-outlined-surface-500" onclick={handleClearSelection}>
					<i class="fa-solid fa-times mr-1"></i>
					{m.clearSelection()}
				</button>
				<div class="flex-1"></div>
				<button class="btn btn-sm preset-ghost-surface" onclick={expandAll}>
					<i class="fa-solid fa-expand mr-1"></i>
					{m.expandAll()}
				</button>
				<button class="btn btn-sm preset-ghost-surface" onclick={collapseAll}>
					<i class="fa-solid fa-compress mr-1"></i>
					{m.collapseAll()}
				</button>
			</div>

			<!-- Legend -->
			<div class="flex flex-wrap items-center gap-4 mb-4 text-xs">
				<div class="flex items-center gap-2">
					<span class="px-2 py-1 rounded-md bg-green-50 border border-green-200 text-green-700">
						<i class="fa-solid fa-square-check mr-1"></i>
						{m.available()}
					</span>
					<span class="text-gray-400">({m.clickToSelect()})</span>
				</div>
				<div class="flex items-center gap-1">
					<span class="px-2 py-1 rounded-md bg-violet-50 border border-violet-200 text-violet-700">
						<i class="fa-solid fa-check mr-1"></i>
						{m.selected()}
					</span>
				</div>
				<div class="flex items-center gap-1">
					<span class="px-2 py-1 rounded-md bg-gray-100 border border-gray-200 text-gray-500">
						<i class="fa-solid fa-lock mr-1"></i>
						{m.alreadyAssigned()}
					</span>
				</div>
			</div>

			<!-- Tree View -->
			<div class="max-h-[600px] overflow-y-auto border rounded-lg p-2 bg-gray-50">
				{#key assignedRequirementIds}
					<RecursiveTreeView
						nodes={treeViewNodes}
						bind:expandedNodes
						hover="hover:bg-gray-100"
						padding="py-2 px-2"
					/>
				{/key}
			</div>
		</div>

		<!-- Right Panel: Assignment Creation & List -->
		<div class="space-y-4">
			<!-- Create/Edit Assignment Card -->
			<div
				class="card bg-white shadow-lg p-4 {editingAssignmentId ? 'ring-2 ring-violet-400' : ''}"
			>
				<h2 class="h4 font-semibold mb-4">
					{#if editingAssignmentId}
						<i class="fa-solid fa-pen text-violet-500 mr-2"></i>
						{m.editAssignment()}
					{:else}
						<i class="fa-solid fa-plus-circle text-primary-500 mr-2"></i>
						{m.newAssignment()}
					{/if}
				</h2>

				<div class="space-y-4">
					<!-- Actor Selection (re-mount on edit mode change so initialValue is captured correctly) -->
					{#key editingAssignmentId}
						<AutocompleteSelect
							form={assignmentSuperForm}
							optionsEndpoint="actors?user__is_third_party=False"
							optionsLabelField="str"
							optionsInfoFields={{
								fields: [{ field: 'type', translate: true }],
								position: 'prefix'
							}}
							field="actor"
							label={m.assignTo()}
							placeholder={m.selectActor()}
							multiple
						/>
					{/key}

					<!-- Selected Count -->
					<div class="bg-gray-50 rounded-lg p-3">
						<div class="flex items-center justify-between text-sm">
							<span class="text-gray-600">{m.selectedRequirements()}:</span>
							<span class="font-semibold text-primary-600">{availableCheckedNodes.length}</span>
						</div>
					</div>

					<!-- Create/Update Button -->
					{#if editingAssignmentId}
						<button
							class="btn preset-filled-primary-500 w-full"
							disabled={!hasSelectedActors || availableCheckedNodes.length === 0 || isUpdating}
							onclick={handleUpdateAssignment}
						>
							{#if isUpdating}
								<i class="fa-solid fa-spinner fa-spin mr-2"></i>
								{m.updating()}
							{:else}
								<i class="fa-solid fa-check mr-2"></i>
								{m.updateAssignment()}
							{/if}
						</button>
						<button class="btn preset-outlined-surface-500 w-full" onclick={cancelEdit}>
							<i class="fa-solid fa-times mr-2"></i>
							{m.cancel()}
						</button>
					{:else}
						<button
							class="btn preset-filled-primary-500 w-full"
							disabled={!hasSelectedActors || availableCheckedNodes.length === 0 || isCreating}
							onclick={handleCreateAssignment}
						>
							{#if isCreating}
								<i class="fa-solid fa-spinner fa-spin mr-2"></i>
								{m.creating()}
							{:else}
								<i class="fa-solid fa-check mr-2"></i>
								{m.createAssignment()}
							{/if}
						</button>
					{/if}

					{#if !hasSelectedActors || availableCheckedNodes.length === 0}
						<p class="text-xs text-gray-500 text-center">
							{m.fillAllFieldsToCreateAssignment()}
						</p>
					{/if}
				</div>
			</div>

			<!-- Existing Assignments Card -->
			<div class="card bg-white shadow-lg p-4">
				<h2 class="h4 font-semibold mb-4">
					<i class="fa-solid fa-list text-primary-500 mr-2"></i>
					{m.existingAssignments()}
					<span class="badge bg-gray-200 text-gray-700 ml-2">{assignments.length}</span>
				</h2>

				{#if assignments.length === 0}
					<div class="text-center py-8 text-gray-500">
						<i class="fa-solid fa-folder-open text-4xl mb-2 opacity-30"></i>
						<p class="text-sm">{m.noAssignmentsYet()}</p>
					</div>
				{:else}
					<div class="space-y-3 max-h-[400px] overflow-y-auto">
						{#each assignments as assignment}
							<div
								class="border rounded-lg p-3 transition-colors {editingAssignmentId ===
								assignment.id
									? 'bg-violet-50 border-violet-300 ring-2 ring-violet-200'
									: 'bg-gray-50 hover:bg-gray-100'}"
							>
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center text-sm text-gray-900 font-medium">
											<i class="fa-solid fa-{actorIcon(assignment.actor)} mr-1"></i>
											<span>{formatActors(assignment.actor)}</span>
										</div>
										<div class="mt-2">
											<button
												class="badge bg-blue-100 text-blue-700 text-xs hover:bg-blue-200 cursor-pointer transition-colors"
												onclick={() => openRequirementsModal(assignment)}
												title={m.clickToViewRequirements()}
											>
												<i class="fa-solid fa-list-ul mr-1"></i>
												{assignment.requirement_assessments.length}
												{m.requirements()}
											</button>
										</div>
									</div>
									<div class="flex items-center gap-1">
										<button
											class="btn btn-sm preset-ghost-surface"
											onclick={() => startEdit(assignment)}
											title={m.edit()}
											disabled={editingAssignmentId !== null}
										>
											<i class="fa-solid fa-pen"></i>
										</button>
										<button
											class="btn btn-sm preset-ghost-error-500"
											onclick={() => handleDeleteAssignment(assignment.id)}
											title={m.delete()}
											disabled={isDeleting === assignment.id || editingAssignmentId !== null}
										>
											{#if isDeleting === assignment.id}
												<i class="fa-solid fa-spinner fa-spin"></i>
											{:else}
												<i class="fa-solid fa-trash"></i>
											{/if}
										</button>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<svelte:window
	onkeydown={(e) => showRequirementsModal && e.key === 'Escape' && closeRequirementsModal()}
/>

<!-- Requirements Detail Modal -->
{#if showRequirementsModal && selectedAssignmentForModal}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/50 z-40"
		onclick={closeRequirementsModal}
		role="presentation"
	></div>

	<!-- Modal -->
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
		<div
			class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b">
				<div>
					<h2 id="modal-title" class="h4 font-semibold">
						<i class="fa-solid fa-{actorIcon(selectedAssignmentForModal.actor)} mr-2"></i>
						{formatActors(selectedAssignmentForModal.actor)}
					</h2>
				</div>
				<button
					class="btn btn-sm preset-ghost-surface"
					onclick={closeRequirementsModal}
					aria-label={m.close()}
				>
					<i class="fa-solid fa-times"></i>
				</button>
			</div>

			<!-- Content -->
			<div class="p-4 overflow-y-auto flex-1">
				<div class="mb-3 flex items-center justify-between">
					<span class="text-sm text-gray-600">
						{m.requirements()}
					</span>
					<span class="badge bg-blue-100 text-blue-700 text-xs">
						{selectedAssignmentForModal.requirement_assessments.length}
						{m.items()}
					</span>
				</div>

				<div class="space-y-2">
					{#each getRequirementDetails(selectedAssignmentForModal.requirement_assessments) as req}
						<div
							class="flex items-center gap-3 p-2 rounded-md bg-gray-50 hover:bg-gray-100 transition-colors"
						>
							<!-- Result indicator -->
							{#if req.result}
								<span
									class="w-2 h-2 rounded-full flex-shrink-0"
									style="background-color: {complianceResultColorMap[req.result] ?? '#9ca3af'};"
									title={req.result}
								></span>
							{:else}
								<span class="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0" title={m.notAssessed()}
								></span>
							{/if}

							<!-- Requirement content -->
							<span class="text-sm text-gray-800">
								{#if req.node_content}
									{req.node_content}
								{:else}
									{req.name}
								{/if}
							</span>
						</div>
					{/each}
				</div>
			</div>

			<!-- Footer -->
			<div class="p-4 border-t bg-gray-50 rounded-b-lg">
				<button class="btn preset-filled-surface-500 w-full" onclick={closeRequirementsModal}>
					{m.close()}
				</button>
			</div>
		</div>
	</div>
{/if}
