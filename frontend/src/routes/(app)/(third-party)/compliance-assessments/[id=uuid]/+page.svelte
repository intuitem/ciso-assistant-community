<script lang="ts">
	import { page } from '$app/stores';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';

	import { onMount } from 'svelte';

	import type {
		ModalComponent,
		ModalSettings,
		ModalStore,
		PopupSettings,
		TreeViewNode
	} from '@skeletonlabs/skeleton';

	import { goto } from '$app/navigation';

	import { getModalStore, popup, SlideToggle } from '@skeletonlabs/skeleton';
	import type { ActionData, PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import TreeViewItemLead from './TreeViewItemLead.svelte';

	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';

	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import type { Node } from './types';

	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	export let data: PageData;
	export let form: ActionData;

	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { displayScoreColor, darkenColor } from '$lib/utils/helpers';
	import { auditFiltersStore, expandedNodesState } from '$lib/utils/stores';
	import { get } from 'svelte/store';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { canPerformAction } from '$lib/utils/access-control';

	$: tree = data.tree;

	$: compliance_assessment_donut_values = data.compliance_assessment_donut_values;

	const user = $page.data.user;
	const model = URL_MODEL_MAP['compliance-assessments'];
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: model.name,
		domain: data.compliance_assessment.folder.id
	});
	const requirementAssessmentModel = URL_MODEL_MAP['requirement-assessments'];
	const canEditRequirementAssessment: boolean = canPerformAction({
		user,
		action: 'change',
		model: requirementAssessmentModel.name,
		domain: data.compliance_assessment.folder.id
	});

	const has_threats = data.threats.total_unique_threats > 0;

	let threatDialogOpen = false;
	let dialogElement;

	function openThreatsDialog() {
		threatDialogOpen = true;
		// Need to use the next tick to ensure the dialog is in the DOM
		setTimeout(() => {
			if (dialogElement) dialogElement.showModal();
		}, 0);
	}

	function closeThreatsDialog() {
		threatDialogOpen = false;
		if (dialogElement) dialogElement.close();
	}

	import ForceCirclePacking from '$lib/components/DataViz/ForceCirclePacking.svelte';

	function handleKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return; // otherwise it will interfere with input fields
		if (event.key === 'f') {
			event.preventDefault();
			goto(`${$page.url.pathname}/flash-mode`);
		}
		if (event.key === 't') {
			event.preventDefault();
			goto(`${$page.url.pathname}/table-mode`);
		}
	}

	onMount(() => {
		// Add event listener to the document
		document.addEventListener('keydown', handleKeydown);

		// Cleanup function to remove event listener
		return () => {
			document.removeEventListener('keydown', handleKeydown);
		};
	});

	const countResults = (
		node: Node,
		resultCounts: Record<string, number> = {}
	): Record<string, number> => {
		if (node.result && node.assessable) {
			resultCounts[node.result] = (resultCounts[node.result] || 0) + 1;
		}
		if (node.status && node.assessable) {
			resultCounts[node.status] = (resultCounts[node.status] || 0) + 1;
		}
		if (node.is_scored && node.assessable && node.result !== 'not_applicable') {
			resultCounts['scored'] = (resultCounts['scored'] || 0) + 1;
			const nodeMeanScore = data.compliance_assessment.show_documentation_score
				? (node.score + node.documentation_score) / 2
				: node.score;
			resultCounts['total_score'] = (resultCounts['total_score'] || 0) + nodeMeanScore;
		}

		if (node.children && Object.keys(node.children).length > 0) {
			for (const childId in node.children) {
				if (Object.prototype.hasOwnProperty.call(node.children, childId)) {
					const childNode = node.children[childId];
					countResults(childNode, resultCounts);
				}
			}
		}
		return resultCounts;
	};

	let id = $page.params.id;

	let filters = get(auditFiltersStore);
	let selectedStatus = filters[id]?.selectedStatus || [];
	let selectedResults = filters[id]?.selectedResults || [];
	let displayOnlyAssessableNodes = filters[id]?.displayOnlyAssessableNodes || false;

	function toggleItem(item, selectedItems) {
		if (selectedItems.includes(item)) {
			return selectedItems.filter((s) => s !== item);
		} else {
			return [...selectedItems, item];
		}
	}

	function toggleStatus(status) {
		selectedStatus = toggleItem(status, selectedStatus);
		auditFiltersStore.setStatus(id, selectedStatus);
	}

	function toggleResult(result) {
		selectedResults = toggleItem(result, selectedResults);
		auditFiltersStore.setResults(id, selectedResults);
	}

	function isNodeHidden(node: Node, displayOnlyAssessableNodes: boolean): boolean {
		const hasAssessableChildren = Object.keys(node.children || {}).length > 0;
		return (
			(displayOnlyAssessableNodes && !node.assessable && !hasAssessableChildren) ||
			(node.assessable &&
				((selectedStatus.length > 0 && !selectedStatus.includes(node.status)) ||
					(selectedResults.length > 0 && !selectedResults.includes(node.result))))
		);
	}
	function transformToTreeView(nodes: Node[]) {
		return nodes.map(([id, node]) => {
			node.resultCounts = countResults(node);
			const hidden = isNodeHidden(node, displayOnlyAssessableNodes);

			console.log(hidden);

			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: {
					...node,
					canEditRequirementAssessment,
					hidden,
					selectedStatus
				},
				lead: TreeViewItemLead,
				leadProps: {
					statusI18n: node.status_i18n,
					resultI18n: node.result_i18n,
					assessable: node.assessable,
					statusColor: complianceStatusColorMap[node.status],
					resultColor: complianceResultColorMap[node.result],
					score: node.score,
					documentationScore: node.documentation_score,
					isScored: node.is_scored,
					showDocumentationScore: data.compliance_assessment.show_documentation_score,
					max_score: node.max_score
				},
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[];
	$: if (tree) {
		treeViewNodes = transformToTreeView(Object.entries(tree));
	}

	function assessableNodesCount(nodes: TreeViewNode[]): number {
		let count = 0;
		for (const node of nodes) {
			if (node.contentProps.assessable) {
				count++;
			}
			if (node.children) {
				count += assessableNodesCount(node.children);
			}
		}
		return count;
	}

	let expandedNodes: TreeViewNode[] = [];

	expandedNodes = $expandedNodesState;
	$: expandedNodesState.set(expandedNodes);

	const popupDownload: PopupSettings = {
		event: 'click',
		target: 'popupDownload',
		placement: 'bottom'
	};

	const modalStore: ModalStore = getModalStore();

	function modalCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.auditCreateForm,
				context: 'fromBaseline',
				model: data.auditModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.createAuditFromBaseline()
		};
		modalStore.trigger(modal);
	}
	let syncingToActionsIsLoading = false;
	async function modalConfirmSyncToActions(
		id: string,
		name: string,
		action: string
	): Promise<void> {
		const requirementAssessmentsSync = await fetch(
			`/compliance-assessments/${$page.params.id}/sync-to-actions`,
			{ method: 'POST' }
		).then((response) => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error('Failed to fetch requirement assessments sync data');
			}
		});
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: data.form,
				id: id,
				debug: false,
				URLModel: 'compliance-assessments',
				formAction: action,
				bodyComponent: List,
				bodyProps: {
					items: Object.values(requirementAssessmentsSync.changes).map(
						(req) => `${req.str}, ${safeTranslate(req.current)} -> ${safeTranslate(req.new)}`
					), //feed this
					message: m.theFollowingChangesWillBeApplied()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.syncToAppliedControls(),
			body: m.syncToAppliedControlsMessage({
				count: data.compliance_assessment.framework.reference_controls.length //change this
			}),
			response: (r: boolean) => {
				syncingToActionsIsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}
	let createAppliedControlsLoading = false;

	function modalConfirmCreateSuggestedControls(id: string, name: string, action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: data.form,
				id: id,
				debug: false,
				URLModel: 'compliance-assessments',
				formAction: action,
				bodyComponent: List,
				bodyProps: {
					items: data.compliance_assessment.framework.reference_controls,
					message: m.theFollowingControlsWillBeAddedColon()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.suggestControls(),
			body: m.createAppliedControlsFromSuggestionsConfirmMessage({
				count: data.compliance_assessment.framework.reference_controls.length
			}),
			response: (r: boolean) => {
				createAppliedControlsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}

	$: if (syncingToActionsIsLoading === true && (form || form?.error))
		syncingToActionsIsLoading = false;
	$: if (createAppliedControlsLoading === true && (form || form?.error))
		createAppliedControlsLoading = false;
	$: if (form?.message?.requirementAssessmentsSync) console.log(form);

	const popupFilter: PopupSettings = {
		event: 'click',
		target: 'popupFilter',
		placement: 'bottom-end',
		closeQuery: '#will-close'
	};

	$: filterCount =
		(selectedStatus.length > 0 ? 1 : 0) +
		(selectedResults.length > 0 ? 1 : 0) +
		(displayOnlyAssessableNodes ? 1 : 0);
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg w-full">
		<div class="flex flex-col space-y-2 whitespace-pre-line w-1/5 pr-1">
			{#each Object.entries(data.compliance_assessment).filter( ([key, _]) => ['ref_id', 'name', 'description', 'perimeter', 'framework', 'authors', 'reviewers', 'status', 'selected_implementation_groups', 'assets'].includes(key) ) as [key, value]}
				<div class="flex flex-col">
					<div
						class="text-sm font-medium text-gray-800 capitalize-first"
						data-testid={key.replaceAll('_', '-') + '-field-title'}
					>
						{safeTranslate(key)}
					</div>
					<ul class="text-sm">
						<li
							class="text-gray-600 list-none"
							data-testid={key.replaceAll('_', '-') + '-field-value'}
						>
							{#if value}
								{#if Array.isArray(value)}
									<ul>
										{#each value as val}
											<li>
												{#if val.str && val.id}
													{@const itemHref = `/${
														URL_MODEL_MAP[data.URLModel]['foreignKeyFields']?.find(
															(item) => item.field === key
														)?.urlModel
													}/${val.id}`}
													{#if !$page.data.user.is_third_party}
														<Anchor href={itemHref} class="anchor">{val.str}</Anchor>
													{:else}
														{val.str}
													{/if}
												{:else}
													{val}
												{/if}
											</li>
										{/each}
									</ul>
								{:else if value.str && value.id}
									{@const itemHref = `/${
										URL_MODEL_MAP['compliance-assessments']['foreignKeyFields']?.find(
											(item) => item.field === key
										)?.urlModel
									}/${value.id}`}
									{#if !$page.data.user.is_third_party}
										<Anchor href={itemHref} class="anchor">{value.str}</Anchor>
									{:else}
										{value.str}
									{/if}
								{:else}
									{safeTranslate(value.str ?? value)}
								{/if}
							{:else}
								--
							{/if}
						</li>
					</ul>
				</div>
			{/each}
		</div>
		{#key compliance_assessment_donut_values}
			<div class="flex w-1/3 relative">
				{#if data.global_score.score >= 0}
					<div class="absolute font-bold text-sm">{m.maturity()}</div>
					<div class="flex justify-center items-center w-full">
						<ProgressRadial
							stroke={100}
							meter={displayScoreColor(data.global_score.score, data.global_score.max_score)}
							font={125}
							value={(data.global_score.score * 100) / data.global_score.max_score}
							width={'w-52'}
						>
							{data.global_score.score}
						</ProgressRadial>
					</div>
				{/if}
			</div>
			<div class="w-1/3">
				<DonutChart
					s_label="Result"
					name="compliance_result"
					title={m.compliance()}
					orientation="horizontal"
					values={compliance_assessment_donut_values.result.values}
					colors={compliance_assessment_donut_values.result.values.map(
						(object) => object.itemStyle.color
					)}
				/>
			</div>
			<div class="w-1/3">
				<DonutChart
					s_label="Status"
					name="compliance_status"
					title={m.progress()}
					orientation="horizontal"
					values={compliance_assessment_donut_values.status.values}
					colors={compliance_assessment_donut_values.status.values.map(
						(object) => object.itemStyle.color
					)}
				/>
			</div>
		{/key}
		<div class="flex flex-col space-y-2 ml-4">
			<div class="flex flex-row space-x-2">
				<button class="btn variant-filled-primary w-full" use:popup={popupDownload}
					><i class="fa-solid fa-download mr-2" />{m.exportButton()}</button
				>
				<div
					class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1 z-10"
					data-popup="popupDownload"
				>
					<p class="block px-4 py-2 text-sm text-gray-800">{m.complianceAssessment()}</p>
					{#if !$page.data.user.is_third_party}
						<a
							href="/compliance-assessments/{data.compliance_assessment.id}/export/csv"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asCSV()}</a
						>
						<a
							href="/compliance-assessments/{data.compliance_assessment.id}/export/word"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asWord()}</a
						>
					{/if}
					<a
						href="/compliance-assessments/{data.compliance_assessment.id}/export"
						class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asZIP()}</a
					>
					{#if !$page.data.user.is_third_party}
						<p class="block px-4 py-2 text-sm text-gray-800">{m.actionPlan()}</p>
						<a
							href="/compliance-assessments/{data.compliance_assessment.id}/action-plan/export/csv"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asCSV()}</a
						>
						<a
							href="/compliance-assessments/{data.compliance_assessment.id}/action-plan/export/pdf"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asPDF()}</a
						>
					{/if}
				</div>
				{#if canEditObject}
					<Anchor
						breadcrumbAction="push"
						href={`${$page.url.pathname}/edit?next=${$page.url.pathname}`}
						class="btn variant-filled-primary h-fit"
						data-testid="edit-button"
						><i class="fa-solid fa-pen-to-square mr-2" /> {m.edit()}</Anchor
					>
				{/if}
			</div>
			{#if !$page.data.user.is_third_party}
				<Anchor
					href={`${$page.url.pathname}/action-plan`}
					class="btn variant-filled-primary h-fit"
					breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2" />{m.actionPlan()}</Anchor
				>
			{/if}
			<span class="pt-4 text-sm">{m.powerUps()}</span>
			{#if !$page.data.user.is_third_party}
				<Anchor
					breadcrumbAction="push"
					href={`${$page.url.pathname}/flash-mode`}
					class="btn text-gray-100 bg-gradient-to-r from-indigo-500 to-violet-500 h-fit"
					><i class="fa-solid fa-bolt mr-2" /> {m.flashMode()}</Anchor
				>
			{/if}
			<Anchor
				breadcrumbAction="push"
				href={`${$page.url.pathname}/table-mode`}
				class="btn text-gray-100 bg-gradient-to-r from-blue-500 to-sky-500 h-fit"
				><i class="fa-solid fa-table-list mr-2" /> {m.tableMode()}</Anchor
			>
			{#if !$page.data.user.is_third_party}
				<button
					class="btn text-gray-100 bg-gradient-to-r from-teal-500 to-emerald-500 h-fit"
					on:click={() => modalCreateForm()}
					><i class="fa-solid fa-diagram-project mr-2" /> {m.applyMapping()}
				</button>
			{/if}

			<button
				class="btn text-gray-100 bg-gradient-to-r from-cyan-500 to-blue-500 h-fit"
				on:click={async () => {
					await modalConfirmSyncToActions(
						data.compliance_assessment.id,
						data.compliance_assessment.name,
						'?/syncToActions'
					);
				}}
			>
				<span class="mr-2">
					{#if syncingToActionsIsLoading}
						<ProgressRadial class="-ml-2" width="w-6" meter="stroke-white" stroke={80} />
					{:else}
						<i class="fa-solid fa-arrows-rotate mr-2"></i>
					{/if}
				</span>
				{m.syncToAppliedControls()}
			</button>

			{#if Object.hasOwn($page.data.user.permissions, 'add_appliedcontrol') && data.compliance_assessment.framework.reference_controls.length > 0}
				<button
					class="btn text-gray-100 bg-gradient-to-r from-purple-500 to-fuchsia-500 h-fit"
					on:click={() => {
						modalConfirmCreateSuggestedControls(
							data.compliance_assessment.id,
							data.compliance_assessment.name,
							'?/createSuggestedControls'
						);
					}}
				>
					<span class="mr-2">
						{#if createAppliedControlsLoading}
							<ProgressRadial class="-ml-2" width="w-6" meter="stroke-white" stroke={80} />
						{:else}
							<i class="fa-solid fa-wand-magic-sparkles"></i>
						{/if}
					</span>
					{m.suggestControls()}
				</button>
			{/if}
			{#if has_threats}
				<button
					class="btn text-gray-100 bg-gradient-to-r from-amber-500 to-orange-500 h-fit"
					on:click={openThreatsDialog}
				>
					<div class="flex items-center space-x-2">
						<i class="fa-solid fa-triangle-exclamation text-red-700"></i>
						<span class="text-red-700 font-bold">{data.threats.total_unique_threats}</span>
						<span>{m.potentialThreats()}</span>
					</div>
				</button>
			{/if}
		</div>
	</div>
	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg">
		<div class="flex flex-row items-center font-semibold justify-between">
			<div>
				<span class="h4">{m.associatedRequirements()}</span>
				<span class="badge variant-soft-primary ml-1">
					{#if treeViewNodes}
						{assessableNodesCount(treeViewNodes)}
					{/if}
				</span>
			</div>
			<button
				use:popup={popupFilter}
				class="btn variant-filled-primary self-end relative"
				id="filters"
			>
				<i class="fa-solid fa-filter mr-2" />
				{m.filters()}
				{#if filterCount}
					<span class="badge absolute -top-0 -right-0 z-10">{filterCount}</span>
				{/if}
			</button>
			<div
				class="card p-2 bg-white w-fit shadow-lg space-y-2 border border-surface-200 z-10"
				data-popup="popupFilter"
			>
				<div>
					<span class="text-sm font-bold">{m.result()}</span>
					<div class="flex flex-wrap gap-2 text-xs bg-gray-100 border-2 p-1 rounded-md">
						{#each Object.entries(complianceResultColorMap) as [result, color]}
							<button
								type="button"
								on:click={() => toggleResult(result)}
								class="px-2 py-1 rounded-md font-bold"
								style="background-color: {selectedResults.includes(result)
									? color
									: 'grey'}; color: {selectedResults.includes(result)
									? result === 'not_applicable'
										? 'white'
										: 'black'
									: 'black'}; opacity: {selectedResults.includes(result) ? 1 : 0.3};"
							>
								{safeTranslate(result)}
							</button>
						{/each}
					</div>
				</div>
				<div>
					<span class="text-sm font-bold">{m.status()}</span>
					<div class="flex flex-wrap w-fit gap-2 text-xs bg-gray-100 border-2 p-1 rounded-md">
						{#each Object.entries(complianceStatusColorMap) as [status, color]}
							<button
								type="button"
								on:click={() => toggleStatus(status)}
								class="px-2 py-1 rounded-md font-bold"
								style="background-color: {selectedStatus.includes(status)
									? color + '44'
									: 'grey'}; color: {selectedStatus.includes(status)
									? darkenColor(color, 0.3)
									: 'black'}; opacity: {selectedStatus.includes(status) ? 1 : 0.3};"
							>
								{safeTranslate(status)}
							</button>
						{/each}
					</div>
				</div>
				<div>
					<span class="text-sm font-bold">{m.ShowOnlyAssessable()}</span>
					<div id="toggle" class="flex items-center space-x-4 text-xs ml-auto mr-4">
						<SlideToggle
							name="questionnaireToggle"
							class="flex flex-row items-center justify-center"
							active="bg-primary-500"
							bind:checked={displayOnlyAssessableNodes}
							on:click={() => {
								displayOnlyAssessableNodes = !displayOnlyAssessableNodes;
								auditFiltersStore.setDisplayOnlyAssessableNodes(id, displayOnlyAssessableNodes);
							}}
						>
							{#if displayOnlyAssessableNodes}
								<span class="font-bold text-xs text-primary-500">{m.yes()}</span>
							{:else}
								<span class="font-bold text-xs text-gray-500">{m.no()}</span>
							{/if}
						</SlideToggle>
					</div>
				</div>
			</div>
		</div>

		<div class="flex items-center my-2 text-xs space-x-2 text-gray-500">
			<i class="fa-solid fa-diagram-project" />
			<p>{m.mappingInferenceTip()}</p>
		</div>
		{#key data}
			{#key displayOnlyAssessableNodes || selectedStatus || selectedResults}
				<RecursiveTreeView
					nodes={transformToTreeView(Object.entries(tree))}
					bind:expandedNodes
					hover="hover:bg-initial"
				/>
			{/key}
		{/key}
	</div>
</div>
{#if threatDialogOpen}
	<dialog
		bind:this={dialogElement}
		class="card p-4 bg-white shadow-2xl w-2/3 max-h-3/4 overflow-auto rounded-lg"
		on:close={() => (threatDialogOpen = false)}
	>
		<div class="flex justify-between items-center mb-4">
			<h3 class="h3 font-bold capitalize">{m.potentialThreats()}</h3>
			<button class="btn btn-sm variant-filled-error" on:click={closeThreatsDialog}>
				<i class="fa-solid fa-times"></i>
			</button>
		</div>

		<div class="threats-content">
			<ForceCirclePacking data={data.threats.graph} name="threats_graph" height="h-[600px]" />
		</div>
	</dialog>
{/if}
