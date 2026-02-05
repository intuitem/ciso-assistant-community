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

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Create superForm instance for AutocompleteSelect - keep full result
	const assignmentSuperForm = superForm(data.assignmentForm, {
		dataType: 'json'
	});
	const { form: assignmentFormStore } = assignmentSuperForm;

	// Create writable stores for checked nodes and assigned nodes, provide via context
	const checkedNodesStore = writable<Set<string>>(new Set());
	setContext('checkedNodes', checkedNodesStore);

	// Assignments from server data
	let assignments = $derived(data.assignments);

	// Track which requirement IDs are already assigned (as a derived store for context)
	let assignedRequirementIds = $derived(
		new Set(assignments.flatMap((assignment) => assignment.requirement_assessments))
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

	// State for assignment creation
	let newAssignmentName = $state('');
	let isCreating = $state(false);
	let isDeleting = $state<string | null>(null);

	// State for requirements detail modal
	let showRequirementsModal = $state(false);
	let selectedAssignmentForModal = $state<typeof assignments[0] | null>(null);

	// Get selected actor ID from form store
	let selectedActorId = $derived($assignmentFormStore.actor ?? '');

	// Get assignment info for a node
	function getAssignmentInfo(nodeId: string): { assignmentName: string; actorName: string } | null {
		for (const assignment of assignments) {
			if (assignment.requirement_assessments.includes(nodeId)) {
				return { assignmentName: assignment.name, actorName: assignment.actor.str };
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
	function buildRequirementLookup(nodes: Record<string, Node>): Map<string, { node_content: string; name: string; result?: string }> {
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
	function getRequirementDetails(requirementIds: string[]): Array<{ id: string; node_content: string; name: string; result?: string }> {
		return requirementIds.map(id => {
			const details = requirementLookup.get(id);
			return {
				id,
				node_content: details?.node_content ?? '',
				name: details?.name ?? 'Unknown',
				result: details?.result
			};
		}).sort((a, b) => a.node_content.localeCompare(b.node_content));
	}

	// Open the requirements modal for an assignment
	function openRequirementsModal(assignment: typeof assignments[0]) {
		selectedAssignmentForModal = assignment;
		showRequirementsModal = true;
	}

	// Close the requirements modal
	function closeRequirementsModal() {
		showRequirementsModal = false;
		selectedAssignmentForModal = null;
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

	function transformToTreeView(nodes: [string, Node][], hasParentNode: boolean = false): TreeViewNode[] {
		return nodes.map(([id, node]) => {
			const nodeId = node.ra_id || id;
			const assignmentInfo = node.ra_id ? getAssignmentInfo(node.ra_id) : null;
			const isAssigned = node.ra_id ? assignedRequirementIds.has(node.ra_id) : false;

			// Get all assessable descendant IDs for batch selection
			const childrenIds = node.assessable ? [] : getAssessableDescendantIds(node);

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
					childrenIds: childrenIds
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
		if (!newAssignmentName.trim() || !selectedActorId || availableCheckedNodes.length === 0) {
			return;
		}

		isCreating = true;
		try {
			const formData = new FormData();
			formData.append('name', newAssignmentName);
			formData.append('actor', selectedActorId);
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
				newAssignmentName = '';
				$assignmentFormStore.actor = undefined;
				$checkedNodesStore = new Set();
				// Apply the action result and refresh page data
				await applyAction(result);
				await invalidateAll();
			} else {
				console.error('Failed to create assignment:', result);
			}
		} catch (error) {
			console.error('Error creating assignment:', error);
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
			} else {
				console.error('Failed to delete assignment:', result);
			}
		} catch (error) {
			console.error('Error deleting assignment:', error);
		} finally {
			isDeleting = null;
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
			<h1 class="h3 font-bold">{m.assignments?.() ?? 'Assignments'}</h1>
		</div>
	</div>

	<!-- Info banner -->
	<div class="alert bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
		<div class="flex items-start">
			<i class="fa-solid fa-info-circle text-blue-600 mr-3 mt-0.5"></i>
			<div class="text-sm">
				<p class="font-medium">{m.aboutAssignments?.() ?? 'About Assignments'}</p>
				<p class="mt-1">
					{m.assignmentsDescription?.() ??
						'Create assignments to delegate groups of requirements to specific actors (users or teams). Once assigned, requirements can only be viewed and managed by the assigned actor.'}
				</p>
			</div>
		</div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
		<!-- Left Panel: Tree with Checkboxes -->
		<div class="lg:col-span-2 card bg-white shadow-lg p-4">
			<div class="flex items-center justify-between mb-4">
				<div>
					<h2 class="h4 font-semibold">{m.requirements?.() ?? 'Requirements'}</h2>
					<p class="text-sm text-gray-500">
						{m.selectRequirementsToAssign?.() ?? 'Select requirements to include in a new assignment'}
					</p>
				</div>
				<div class="flex items-center space-x-2">
					<span class="badge bg-violet-100 text-violet-700 px-2 py-1 text-xs">
						{availableCheckedNodes.length}
						{m.selected?.() ?? 'selected'}
					</span>
				</div>
			</div>

			<!-- Tree controls -->
			<div class="flex flex-wrap items-center gap-2 mb-4 pb-4 border-b">
				<button
					class="btn btn-sm preset-outlined-primary-500"
					onclick={handleSelectAll}
				>
					<i class="fa-solid fa-check-double mr-1"></i>
					{m.selectAllAvailable?.() ?? 'Select All Available'}
				</button>
				<button
					class="btn btn-sm preset-outlined-surface-500"
					onclick={handleClearSelection}
				>
					<i class="fa-solid fa-times mr-1"></i>
					{m.clearSelection?.() ?? 'Clear'}
				</button>
				<div class="flex-1"></div>
				<button class="btn btn-sm preset-ghost-surface" onclick={expandAll}>
					<i class="fa-solid fa-expand mr-1"></i>
					{m.expandAll?.() ?? 'Expand All'}
				</button>
				<button class="btn btn-sm preset-ghost-surface" onclick={collapseAll}>
					<i class="fa-solid fa-compress mr-1"></i>
					{m.collapseAll?.() ?? 'Collapse All'}
				</button>
			</div>

			<!-- Legend -->
			<div class="flex flex-wrap items-center gap-4 mb-4 text-xs">
				<div class="flex items-center gap-2">
					<span class="px-2 py-1 rounded-md bg-green-50 border border-green-200 text-green-700">
						<i class="fa-solid fa-square-check mr-1"></i>
						{m.available?.() ?? 'Available'}
					</span>
					<span class="text-gray-400">({m.clickToSelect?.() ?? 'click to select'})</span>
				</div>
				<div class="flex items-center gap-1">
					<span class="px-2 py-1 rounded-md bg-violet-50 border border-violet-200 text-violet-700">
						<i class="fa-solid fa-check mr-1"></i>
						{m.selected?.() ?? 'Selected'}
					</span>
				</div>
				<div class="flex items-center gap-1">
					<span class="px-2 py-1 rounded-md bg-gray-100 border border-gray-200 text-gray-500">
						<i class="fa-solid fa-lock mr-1"></i>
						{m.alreadyAssigned?.() ?? 'Already assigned'}
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
			<!-- Create Assignment Card -->
			<div class="card bg-white shadow-lg p-4">
				<h2 class="h4 font-semibold mb-4">
					<i class="fa-solid fa-plus-circle text-primary-500 mr-2"></i>
					{m.newAssignment?.() ?? 'New Assignment'}
				</h2>

				<div class="space-y-4">
					<!-- Assignment Name -->
					<div>
						<label for="assignment-name" class="text-sm font-medium text-gray-700">
							{m.name?.() ?? 'Name'} <span class="text-red-500">*</span>
						</label>
						<input
							id="assignment-name"
							type="text"
							class="input mt-1 w-full"
							placeholder={m.enterAssignmentName?.() ?? 'Enter assignment name...'}
							bind:value={newAssignmentName}
							disabled={isCreating}
						/>
					</div>

					<!-- Actor Selection -->
					<AutocompleteSelect
						form={assignmentSuperForm}
						optionsEndpoint="actors?user__is_third_party=False"
						optionsLabelField="str"
						optionsInfoFields={{
							fields: [{ field: 'type', translate: true }],
							position: 'prefix'
						}}
						field="actor"
						label={m.assignTo?.() ?? 'Assign To'}
						placeholder={m.selectActor?.() ?? 'Search for an actor...'}
					/>

					<!-- Selected Count -->
					<div class="bg-gray-50 rounded-lg p-3">
						<div class="flex items-center justify-between text-sm">
							<span class="text-gray-600">{m.selectedRequirements?.() ?? 'Selected requirements'}:</span>
							<span class="font-semibold text-primary-600">{availableCheckedNodes.length}</span>
						</div>
					</div>

					<!-- Create Button -->
					<button
						class="btn preset-filled-primary-500 w-full"
						disabled={!newAssignmentName.trim() || !selectedActorId || availableCheckedNodes.length === 0 || isCreating}
						onclick={handleCreateAssignment}
					>
						{#if isCreating}
							<i class="fa-solid fa-spinner fa-spin mr-2"></i>
							{m.creating?.() ?? 'Creating...'}
						{:else}
							<i class="fa-solid fa-check mr-2"></i>
							{m.createAssignment?.() ?? 'Create Assignment'}
						{/if}
					</button>

					{#if !newAssignmentName.trim() || !selectedActorId || availableCheckedNodes.length === 0}
						<p class="text-xs text-gray-500 text-center">
							{m.fillAllFieldsToCreateAssignment?.() ??
								'Fill in the name, select an actor, and select at least one requirement'}
						</p>
					{/if}
				</div>
			</div>

			<!-- Existing Assignments Card -->
			<div class="card bg-white shadow-lg p-4">
				<h2 class="h4 font-semibold mb-4">
					<i class="fa-solid fa-list text-primary-500 mr-2"></i>
					{m.existingAssignments?.() ?? 'Existing Assignments'}
					<span class="badge bg-gray-200 text-gray-700 ml-2">{assignments.length}</span>
				</h2>

				{#if assignments.length === 0}
					<div class="text-center py-8 text-gray-500">
						<i class="fa-solid fa-folder-open text-4xl mb-2 opacity-30"></i>
						<p class="text-sm">{m.noAssignmentsYet?.() ?? 'No assignments created yet'}</p>
					</div>
				{:else}
					<div class="space-y-3 max-h-[400px] overflow-y-auto">
						{#each assignments as assignment}
							<div class="border rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition-colors">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<h3 class="font-medium text-gray-900">{assignment.name}</h3>
										<div class="flex items-center mt-1 text-sm text-gray-600">
											<i class="fa-solid fa-{assignment.actor.type === 'user' ? 'user' : 'users'} mr-1"></i>
											<span>{assignment.actor.str}</span>
										</div>
										<div class="mt-2">
											<button
												class="badge bg-blue-100 text-blue-700 text-xs hover:bg-blue-200 cursor-pointer transition-colors"
												onclick={() => openRequirementsModal(assignment)}
												title={m.clickToViewRequirements?.() ?? 'Click to view requirements'}
											>
												<i class="fa-solid fa-list-ul mr-1"></i>
												{assignment.requirement_assessments.length}
												{m.requirements?.() ?? 'requirements'}
											</button>
										</div>
									</div>
									<button
										class="btn btn-sm preset-ghost-error-500"
										onclick={() => handleDeleteAssignment(assignment.id)}
										title={m.delete?.() ?? 'Delete'}
										disabled={isDeleting === assignment.id}
									>
										{#if isDeleting === assignment.id}
											<i class="fa-solid fa-spinner fa-spin"></i>
										{:else}
											<i class="fa-solid fa-trash"></i>
										{/if}
									</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<!-- Requirements Detail Modal -->
{#if showRequirementsModal && selectedAssignmentForModal}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/50 z-40"
		onclick={closeRequirementsModal}
		onkeydown={(e) => e.key === 'Escape' && closeRequirementsModal()}
		role="button"
		tabindex="-1"
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
						{selectedAssignmentForModal.name}
					</h2>
					<p class="text-sm text-gray-500 mt-1">
						<i class="fa-solid fa-{selectedAssignmentForModal.actor.type === 'user' ? 'user' : 'users'} mr-1"></i>
						{m.assignedTo?.() ?? 'Assigned to'}: {selectedAssignmentForModal.actor.str}
					</p>
				</div>
				<button
					class="btn btn-sm preset-ghost-surface"
					onclick={closeRequirementsModal}
					aria-label={m.close?.() ?? 'Close'}
				>
					<i class="fa-solid fa-times"></i>
				</button>
			</div>

			<!-- Content -->
			<div class="p-4 overflow-y-auto flex-1">
				<div class="mb-3 flex items-center justify-between">
					<span class="text-sm text-gray-600">
						{m.requirements?.() ?? 'Requirements'}
					</span>
					<span class="badge bg-blue-100 text-blue-700 text-xs">
						{selectedAssignmentForModal.requirement_assessments.length} {m.items?.() ?? 'items'}
					</span>
				</div>

				<div class="space-y-2">
					{#each getRequirementDetails(selectedAssignmentForModal.requirement_assessments) as req}
						<div class="flex items-center gap-3 p-2 rounded-md bg-gray-50 hover:bg-gray-100 transition-colors">
							<!-- Result indicator -->
							{#if req.result}
								<span
									class="w-2 h-2 rounded-full flex-shrink-0"
									style="background-color: {complianceResultColorMap[req.result] ?? '#9ca3af'};"
									title={req.result}
								></span>
							{:else}
								<span class="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0" title="Not assessed"></span>
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
				<button
					class="btn preset-filled-surface-500 w-full"
					onclick={closeRequirementsModal}
				>
					{m.close?.() ?? 'Close'}
				</button>
			</div>
		</div>
	</div>
{/if}
