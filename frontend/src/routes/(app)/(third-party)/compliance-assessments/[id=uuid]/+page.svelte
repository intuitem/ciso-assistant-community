<script lang="ts">
	import { run } from 'svelte/legacy';

	import { page } from '$app/state';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';

	import { onMount } from 'svelte';

	import type { ModalComponent, ModalSettings, TreeViewNode } from '@skeletonlabs/skeleton-svelte';

	import { Switch, Progress, Popover, Tooltip } from '@skeletonlabs/skeleton-svelte';

	import { goto, invalidateAll } from '$app/navigation';

	import {} from '@skeletonlabs/skeleton-svelte';
	import type { ActionData, PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import TreeViewItemLead from './TreeViewItemLead.svelte';

	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';

	import {
		complianceResultColorMap,
		complianceStatusColorMap,
		extendedResultColorMap
	} from '$lib/utils/constants';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RingProgress from '$lib/components/DataViz/RingProgress.svelte';
	import { URL_MODEL_MAP, getModelInfo } from '$lib/utils/crud';
	import type { Node } from './types';

	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';

	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { displayScoreColor, darkenColor, getScoreHexColor } from '$lib/utils/helpers';
	import { auditFiltersStore, expandedNodesState } from '$lib/utils/stores';
	import { derived } from 'svelte/store';
	import { canPerformAction } from '$lib/utils/access-control';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import ValidationFlowsSection from '$lib/components/ValidationFlows/ValidationFlowsSection.svelte';
	import { countMasked, isMaskedPlaceholder } from '$lib/utils/related-visibility';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const compliance_assessment = $derived(data.compliance_assessment);

	const user = page.data.user;
	const model = URL_MODEL_MAP['compliance-assessments'];
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: model.name,
		domain: compliance_assessment.folder.id
	});
	const requirementAssessmentModel = URL_MODEL_MAP['requirement-assessments'];
	const canEditRequirementAssessment: boolean =
		!data.compliance_assessment.is_locked &&
		canPerformAction({
			user,
			action: 'change',
			model: requirementAssessmentModel.name,
			domain: data.compliance_assessment.folder.id
		});

	const has_threats = data.threats.total_unique_threats > 0;

	const objectsNotVisibleLabel = (count: number): string => {
		return m.objectsNotVisible({ count });
	};

	let threatDialogOpen = $state(false);
	let dialogElement = $state();

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
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import CompareAuditModal from '$lib/components/Modals/CompareAuditModal.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';

	function handleKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return; // otherwise it will interfere with input fields
		if (event.key === 'f') {
			event.preventDefault();
			goto(`${page.url.pathname}/flash-mode`);
		}
		if (event.key === 't') {
			event.preventDefault();
			goto(`${page.url.pathname}/table-mode`);
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
			const weight = node.weight || 1;
			resultCounts['scored'] = (resultCounts['scored'] || 0) + 1;
			resultCounts['total_weight'] = (resultCounts['total_weight'] || 0) + weight;
			const nodeDocumentationScore = data.compliance_assessment.show_documentation_score
				? node.documentation_score
				: 0;
			resultCounts['total_documentation_score'] =
				(resultCounts['total_documentation_score'] || 0) + (nodeDocumentationScore || 0) * weight;
			resultCounts['total_score'] = (resultCounts['total_score'] || 0) + (node.score || 0) * weight;
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

	let id = $state(page.params.id);
	// derive the current filters for this audit ID
	const currentFilters = derived(auditFiltersStore, ($f) => $f[id] ?? {});
	// reactive values that update whenever auditFiltersStore changes
	let selectedStatus = $state([]);
	let selectedResults = $state([]);
	let selectedExtendedResults = $state([]);
	let displayOnlyAssessableNodes = $state(false);
	$effect(
		() =>
			({
				selectedStatus = [],
				selectedResults = [],
				selectedExtendedResults = [],
				displayOnlyAssessableNodes = false
			} = $currentFilters)
	);

	function toggleItem(item, selectedItems) {
		if (selectedItems.includes(item)) {
			return selectedItems.filter((s) => s !== item);
		} else {
			return [...selectedItems, item];
		}
	}

	function toggleStatus(status) {
		selectedStatus = toggleItem(status, selectedStatus);
		auditFiltersStore.setStatus(page.params.id, selectedStatus);
	}

	function toggleResult(result) {
		selectedResults = toggleItem(result, selectedResults);
		auditFiltersStore.setResults(page.params.id, selectedResults);
	}

	function toggleExtendedResult(extendedResult) {
		selectedExtendedResults = toggleItem(extendedResult, selectedExtendedResults);
		auditFiltersStore.setExtendedResults(page.params.id, selectedExtendedResults);
	}

	function isNodeHidden(node: Node, displayOnlyAssessableNodes: boolean): boolean {
		const hasAssessableChildren = Object.keys(node.children || {}).length > 0;
		return (
			(displayOnlyAssessableNodes && !node.assessable && !hasAssessableChildren) ||
			(node.assessable &&
				((selectedStatus.length > 0 && !selectedStatus.includes(node.status)) ||
					(selectedResults.length > 0 && !selectedResults.includes(node.result)) ||
					(selectedExtendedResults.length > 0 &&
						!selectedExtendedResults.includes(node.extended_result))))
		);
	}
	function transformToTreeView(nodes: Node[], hasParentNode: boolean = false) {
		return nodes.map(([id, node]) => {
			node.resultCounts = countResults(node);
			const hidden = isNodeHidden(node, displayOnlyAssessableNodes);

			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: {
					...node,
					canEditRequirementAssessment,
					hasParentNode,
					showDocumentationScore: data.compliance_assessment.show_documentation_score,
					scoringEnabled: data.compliance_assessment.scoring_enabled,
					scoreCalculationMethod: data.compliance_assessment.score_calculation_method,
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
					scoringEnabled: data.compliance_assessment.scoring_enabled,
					showDocumentationScore: data.compliance_assessment.show_documentation_score,
					max_score: node.max_score,
					progressStatusEnabled: data.compliance_assessment.progress_status_enabled,
					extendedResultEnabled: data.compliance_assessment.extended_result_enabled,
					extendedResult: node.extended_result,
					extendedResultColor: extendedResultColorMap[node.extended_result]
				},
				children: node.children ? transformToTreeView(Object.entries(node.children), true) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[] = $state();

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

	let expandedNodes: TreeViewNode[] = $state([]);

	expandedNodes = $expandedNodesState;

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

	function modalCreateCloneForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.auditCloneForm,
				context: 'clone',
				model: data.auditModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.cloneAudit()
		};
		modalStore.trigger(modal);
	}

	function modalCompareAudit(): void {
		const modalComponent: ModalComponent = {
			ref: CompareAuditModal,
			props: {
				currentAudit: data.compliance_assessment
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent
		};
		modalStore.trigger(modal);
	}

	function modalRequestValidation(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.validationFlowForm,
				model: getModelInfo('validation-flows'),
				formAction: '/validation-flows?/create',
				invalidateAll: true,
				onConfirm: async () => {
					await invalidateAll();
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.requestValidation()
		};
		modalStore.trigger(modal);
	}
	let syncingToActionsIsLoading = $state(false);
	async function modalConfirmSyncToActions(
		id: string,
		name: string,
		action: string
	): Promise<void> {
		const requirementAssessmentsSync = await fetch(
			`/compliance-assessments/${page.params.id}/sync-to-actions`,
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
						({ str, changes }) =>
							`${str}: ${changes
								.map((change) => `${safeTranslate(change.current)} 🠲 ${safeTranslate(change.new)}`)
								.join(' | ')}`
					),
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
	let createAppliedControlsLoading = $state(false);

	async function modalConfirmCreateSuggestedControls(id: string, name: string, action: string) {
		let previewItems: string[] = [];
		try {
			const previewResponse = await fetch(
				`/compliance-assessments/${id}/suggestions/applied-controls?dry_run=true`
			);
			if (previewResponse.ok) {
				const previewData: any[] = await previewResponse.json();
				previewItems = previewData.map(
					(control) =>
						control?.name ||
						control?.reference_control?.str ||
						control?.reference_control?.name ||
						control?.ref_id ||
						''
				);
			} else {
				throw new Error(await previewResponse.text());
			}
		} catch (error) {
			console.error('Unable to fetch suggested controls preview', error);
			previewItems = data.compliance_assessment.framework.reference_controls.map(
				(control) =>
					control?.name ||
					control?.reference_control?.str ||
					control?.reference_control?.name ||
					control?.ref_id ||
					''
			);
		}

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
					items: previewItems,
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
				count: previewItems.length
			}),
			response: (r: boolean) => {
				createAppliedControlsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}

	let tree = $derived(data.tree);
	let compliance_assessment_donut_values = $derived(data.compliance_assessment_donut_values);

	let exportPopupOpen = $state(false);
	let filterPopupOpen = $state(false);

	run(() => {
		if (tree) {
			treeViewNodes = transformToTreeView(Object.entries(tree));
		}
	});
	run(() => {
		expandedNodesState.set(expandedNodes);
	});
	run(() => {
		if (syncingToActionsIsLoading === true && (form || form?.error))
			syncingToActionsIsLoading = false;
	});
	run(() => {
		if (createAppliedControlsLoading === true && (form || form?.error))
			createAppliedControlsLoading = false;
	});

	let filterCount = $derived(
		(selectedStatus.length > 0 ? 1 : 0) +
			(selectedResults.length > 0 ? 1 : 0) +
			(selectedExtendedResults.length > 0 ? 1 : 0) +
			(displayOnlyAssessableNodes ? 1 : 0)
	);

	let hasNonVisibleObjects = $derived(() => {
		if (!canEditObject) return false;
		for (const [key, value] of Object.entries(data.compliance_assessment)) {
			if (Array.isArray(value)) {
				const maskedCount = countMasked(value);
				if (maskedCount > 0) return true;
			} else if (isMaskedPlaceholder(value)) {
				return true;
			}
		}
		return false;
	});
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	{#if data.compliance_assessment.is_locked}
		<div
			class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg shadow-sm"
		>
			<div class="flex items-center">
				<i class="fa-solid fa-lock text-yellow-600 mr-2"></i>
				<span class="font-medium">{m.lockedAssessment()}</span>
				<span class="ml-2 text-sm">{m.lockedAssessmentMessage()}</span>
			</div>
		</div>
	{/if}

	<div class="flex flex-col card px-6 py-4 bg-white shadow-lg w-full">
		<div class="flex flex-row justify-between">
			<div class="flex flex-col space-y-2 whitespace-pre-line w-1/5 pr-1">
				{#each Object.entries(data.compliance_assessment).filter(([key, value]) => {
					const fieldsToShow = ['ref_id', 'name', 'description', 'version', 'folder', 'perimeter', 'framework', 'authors', 'reviewers', 'status', 'selected_implementation_groups', 'campaign'];
					if (!fieldsToShow.includes(key)) return false;
					// Hide selected_implementation_groups if framework doesn't support implementation groups
					if (key === 'selected_implementation_groups' && (!data.compliance_assessment.framework.implementation_groups_definition || !Array.isArray(data.compliance_assessment.framework.implementation_groups_definition) || data.compliance_assessment.framework.implementation_groups_definition.length === 0)) return false;
					return true;
				}) as [key, value]}
					{@const isUpdatableFramework = key === 'framework' && value.has_update}
					<div class="flex flex-col">
						<div
							class="text-sm font-medium text-gray-800 capitalize-first"
							data-testid={key.replaceAll('_', '-') + '-field-title'}
						>
							{#if isUpdatableFramework}
								<i title={m.updateAvailable()} class="fa-solid fa-circle-up text-success-600-400"
								></i>
							{/if}
							{safeTranslate(key)}
							{#if isUpdatableFramework}
								({m.updateAvailable()})
							{/if}
						</div>
						<ul class="text-sm">
							<li
								class="text-gray-600 list-none"
								data-testid={key.replaceAll('_', '-') + '-field-value'}
							>
								{#if value}
									{#if Array.isArray(value)}
										{@const hiddenCount = countMasked(value)}
										{@const visibleValues = value.filter((item) => !isMaskedPlaceholder(item))}
										{#if visibleValues.length > 0}
											<ul>
												{#each visibleValues as val}
													<li>
														{#if val.str && val.id}
															{@const itemHref = `/${
																URL_MODEL_MAP[data.URLModel]['foreignKeyFields']?.find(
																	(item) => item.field === key
																)?.urlModel
															}/${val.id}`}
															{#if !page.data.user.is_third_party}
																<Anchor href={itemHref} class="anchor">{val.str}</Anchor>
															{:else}
																{val.str}
															{/if}
														{:else if val.str}
															{val.str}
														{:else}
															{safeTranslate(val)}
														{/if}
													</li>
												{/each}
											</ul>
											{#if hiddenCount > 0}
												<p class="mt-1 text-xs text-yellow-700">
													{objectsNotVisibleLabel(hiddenCount)}
												</p>
											{/if}
										{:else if hiddenCount > 0}
											<p class="text-xs text-yellow-700">
												{objectsNotVisibleLabel(hiddenCount)}
											</p>
										{:else}
											--
										{/if}
									{:else if value.str && value.id}
										{@const itemHref = `/${
											URL_MODEL_MAP['compliance-assessments']['foreignKeyFields']?.find(
												(item) => item.field === key
											)?.urlModel
										}/${value.id}`}
										{#if !page.data.user.is_third_party}
											<Anchor href={itemHref} class="anchor">{value.str}</Anchor>
										{:else}
											{value.str}
										{/if}
									{:else if isMaskedPlaceholder(value)}
										<p class="text-xs text-yellow-700">{objectsNotVisibleLabel(1)}</p>
									{:else if key === 'description'}
										<MarkdownRenderer content={value} />
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
				<div>
					<div class="font-medium">{m.createdAt()}</div>
					{formatDateOrDateTime(data.compliance_assessment.created_at, getLocale())}
				</div>
				{#if page.data?.featureflags?.validation_flows}
					{#key compliance_assessment.validation_flows}
						<ValidationFlowsSection validationFlows={compliance_assessment.validation_flows} />
					{/key}
				{/if}
			</div>
			{#key compliance_assessment_donut_values}
				{#if data.global_score && data.global_score.maturity_score >= 0}
					<div class="w-1/4">
						<RingProgress
							name="global_maturity"
							value={data.global_score.maturity_score}
							max={data.global_score.total_max_score}
							color={getScoreHexColor(
								data.global_score.maturity_score,
								data.global_score.total_max_score
							)}
							strokeWidth={35}
							fontSize={36}
							title={m.maturity()}
						/>
					</div>
				{/if}
				<div class={data.compliance_assessment.extended_result_enabled ? 'w-1/4' : 'w-1/3'}>
					<DonutChart
						s_label="Result"
						name="compliance_result"
						title={m.compliance()}
						orientation="horizontal"
						values={compliance_assessment_donut_values.result.values}
						colors={compliance_assessment_donut_values.result.values.map(
							(object) => object.itemStyle.color
						)}
						showPercentage={true}
					/>
				</div>
				{#if data.compliance_assessment.extended_result_enabled && compliance_assessment_donut_values.extended_result?.values?.length > 0}
					<div class="w-1/4">
						<DonutChart
							s_label="Extended Result"
							name="compliance_extended_result"
							title={m.extendedResult()}
							orientation="horizontal"
							values={compliance_assessment_donut_values.extended_result.values}
							colors={compliance_assessment_donut_values.extended_result.values.map(
								(object) => object.itemStyle.color
							)}
							showPercentage={true}
						/>
					</div>
				{/if}
				{#if data.compliance_assessment.progress_status_enabled}
					<div class={data.compliance_assessment.extended_result_enabled ? 'w-1/4' : 'w-1/3'}>
						<DonutChart
							s_label="Status"
							name="compliance_status"
							title={m.progress()}
							orientation="horizontal"
							values={compliance_assessment_donut_values.status.values}
							colors={compliance_assessment_donut_values.status.values.map(
								(object) => object.itemStyle.color
							)}
							showPercentage={true}
						/>
					</div>
				{/if}
			{/key}
			<div class="flex flex-col space-y-2 ml-4">
				<div class="flex flex-row space-x-2">
					<Popover
						open={exportPopupOpen}
						onOpenChange={(e) => (exportPopupOpen = e.open)}
						positioning={{ placement: 'bottom' }}
					>
						<Popover.Trigger class="btn preset-filled-primary-500 w-full">
							<span data-testid="export-button">
								<i class="fa-solid fa-download mr-2"></i>{m.exportButton()}
							</span>
						</Popover.Trigger>
						<Popover.Positioner>
							<Popover.Content
								class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
							>
								<div>
									<p class="block px-4 py-2 text-sm text-gray-800">{m.complianceAssessment()}</p>
									{#if !page.data.user.is_third_party}
										<a
											href="/compliance-assessments/{data.compliance_assessment.id}/export/csv"
											class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
											>... {m.asCSV()}</a
										>
										<a
											href="/compliance-assessments/{data.compliance_assessment.id}/export/xlsx"
											class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
											>... {m.asXLSX()}</a
										>
										<a
											href="/compliance-assessments/{data.compliance_assessment.id}/export/word"
											class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
											>... {m.asWord()}</a
										>
									{/if}
									<a
										href="/compliance-assessments/{data.compliance_assessment.id}/export"
										class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
										>... {m.asZIP()}</a
									>
									{#if !page.data.user.is_third_party}
										<p class="block px-4 py-2 text-sm text-gray-800">{m.actionPlan()}</p>
										<a
											href="/compliance-assessments/{data.compliance_assessment
												.id}/action-plan/export/csv"
											class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
											>... {m.asCSV()}</a
										>
										<a
											href="/compliance-assessments/{data.compliance_assessment
												.id}/action-plan/export/xlsx"
											class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
											>... {m.asXLSX()}</a
										>
										<a
											href="/compliance-assessments/{data.compliance_assessment
												.id}/action-plan/export/pdf"
											class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
											>... {m.asPDF()}</a
										>
									{/if}
								</div>
							</Popover.Content>
						</Popover.Positioner>
					</Popover>
					{#if canEditObject}
						<Anchor
							breadcrumbAction="push"
							href={`${page.url.pathname}/edit?next=${page.url.pathname}`}
							class="btn preset-filled-primary-500 h-fit"
							data-testid="edit-button"
							><i class="fa-solid fa-pen-to-square mr-2"></i> {m.edit()}</Anchor
						>
					{/if}
				</div>
				{#if !page.data.user.is_third_party}
					<Anchor
						href={`${page.url.pathname}/action-plan`}
						class="btn preset-filled-primary-500 h-fit"
						breadcrumbAction="push"
						data-testid="action-plan-button"
						><i class="fa-solid fa-heart-pulse mr-2"></i>{m.actionPlan()}</Anchor
					>
					<Anchor
						href={`${page.url.pathname}/evidences-list`}
						class="btn preset-filled-secondary-500 h-fit"
						breadcrumbAction="push"
						><i class="fa-solid fa-file-lines mr-2"></i>{m.evidences()}</Anchor
					>
				{/if}
				<!-- Power-ups Command Palette Grid -->
				<div class="pt-3 border-t border-gray-200 mt-2 space-y-3">
					<span class="text-xs font-semibold text-gray-400 uppercase tracking-widest select-none"
						>{m.powerUps()}</span
					>

					<!-- Modes -->
					{#if !data.compliance_assessment.is_locked}
						<div>
							<span
								class="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1.5 block"
								>{m.modes()}</span
							>
							<div class="grid grid-cols-2 gap-2">
								{#if !page.data.user.is_third_party}
									<Anchor
										breadcrumbAction="push"
										href={`${page.url.pathname}/flash-mode`}
										class="flex items-center gap-3 px-3.5 py-3 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-700 hover:bg-indigo-100 hover:border-indigo-200 transition-colors cursor-pointer"
										data-testid="flash-mode-button"
									>
										<div
											class="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-500 text-white shrink-0"
										>
											<i class="fa-solid fa-bolt text-sm"></i>
										</div>
										<span class="text-sm font-semibold">{m.flashMode()}</span>
									</Anchor>
								{/if}
								<Anchor
									breadcrumbAction="push"
									href={`${page.url.pathname}/table-mode`}
									class="flex items-center gap-3 px-3.5 py-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-700 hover:bg-slate-100 hover:border-slate-200 transition-colors cursor-pointer"
									data-testid="table-mode-button"
								>
									<div
										class="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-500 text-white shrink-0"
									>
										<i class="fa-solid fa-table-list text-sm"></i>
									</div>
									<span class="text-sm font-semibold">{m.tableMode()}</span>
								</Anchor>
							</div>
						</div>
					{/if}

					<!-- Actions -->
					{#if !page.data.user.is_third_party}
						<div>
							<span
								class="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1.5 block"
								>{m.actions()}</span
							>
							<div class="grid grid-cols-2 gap-2">
								<button
									class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors shadow-sm cursor-pointer text-left"
									onclick={() => modalCreateForm()}
									data-testid="apply-mapping-button"
								>
									<i class="fa-solid fa-diagram-project text-emerald-500 text-base"></i>
									<span class="text-sm font-medium">{m.applyMapping()}</span>
								</button>
								<button
									class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors shadow-sm cursor-pointer text-left"
									onclick={() => modalCreateCloneForm()}
									data-testid="clone-audit-button"
								>
									<i class="fa-solid fa-copy text-fuchsia-500 text-base"></i>
									<span class="text-sm font-medium">{m.cloneAudit()}</span>
								</button>
								<button
									class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors shadow-sm cursor-pointer text-left"
									onclick={() => modalCompareAudit()}
									data-testid="compare-audit-button"
								>
									<i class="fa-solid fa-code-compare text-rose-500 text-base"></i>
									<span class="text-sm font-medium">{m.compareToAudit()}</span>
								</button>
								{#if page.data?.featureflags?.validation_flows}
									<button
										class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors shadow-sm cursor-pointer text-left"
										onclick={() => modalRequestValidation()}
										data-testid="request-validation-button"
									>
										<i class="fa-solid fa-check-circle text-amber-500 text-base"></i>
										<span class="text-sm font-medium">{m.requestValidation()}</span>
									</button>
								{/if}
								{#if !data.compliance_assessment.is_locked}
									<button
										class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors shadow-sm cursor-pointer text-left"
										data-testid="sync-to-actions-button"
										onclick={async () => {
											await modalConfirmSyncToActions(
												data.compliance_assessment.id,
												data.compliance_assessment.name,
												'?/syncToActions'
											);
										}}
									>
										{#if syncingToActionsIsLoading}
											<Progress value={null}>
												<Progress.Circle class="[--size:--spacing(5)]">
													<Progress.CircleTrack />
													<Progress.CircleRange class="stroke-cyan-500" />
												</Progress.Circle>
											</Progress>
										{:else}
											<i class="fa-solid fa-arrows-rotate text-cyan-500 text-base"></i>
										{/if}
										<span class="text-sm font-medium">{m.syncToAppliedControls()}</span>
									</button>
									{#if Object.hasOwn(page.data.user.permissions, 'add_appliedcontrol') && data.compliance_assessment.framework.reference_controls.length > 0}
										<button
											class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors shadow-sm cursor-pointer text-left"
											onclick={() => {
												modalConfirmCreateSuggestedControls(
													data.compliance_assessment.id,
													data.compliance_assessment.name,
													'?/createSuggestedControls'
												);
											}}
										>
											{#if createAppliedControlsLoading}
												<Progress value={null}>
													<Progress.Circle class="[--size:--spacing(5)]">
														<Progress.CircleTrack />
														<Progress.CircleRange class="stroke-violet-500" />
													</Progress.Circle>
												</Progress>
											{:else}
												<i class="fa-solid fa-wand-magic-sparkles text-violet-500 text-base"></i>
											{/if}
											<span class="text-sm font-medium">{m.suggestControls()}</span>
										</button>
									{/if}
								{/if}
								{#if canEditObject && page.data?.featureflags?.auditee_mode && !data.compliance_assessment.is_locked && data.compliance_assessment.status !== 'in_review'}
									<Anchor
										breadcrumbAction="push"
										href={`${page.url.pathname}/assignments`}
										class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors shadow-sm cursor-pointer text-left"
										data-testid="assignments-button"
									>
										<i class="fa-solid fa-user-tag text-green-500 text-base"></i>
										<span class="text-sm font-medium">{m.assignments()}</span>
									</Anchor>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Insights -->
					{#if (has_threats || page.data?.featureflags?.advanced_analytics) && !page.data.user.is_third_party}
						<div>
							<span
								class="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-1.5 block"
								>{m.insights()}</span
							>
							<div class="grid grid-cols-2 gap-2">
								{#if has_threats && !page.data.user.is_third_party}
									<button
										class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 hover:bg-amber-100 transition-colors cursor-pointer text-left"
										onclick={openThreatsDialog}
									>
										<div
											class="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500 text-white shrink-0"
										>
											<i class="fa-solid fa-triangle-exclamation text-sm"></i>
										</div>
										<div class="flex flex-col">
											<span class="text-lg font-bold leading-tight"
												>{data.threats.total_unique_threats}</span
											>
											<span class="text-xs text-amber-600">{m.potentialThreats()}</span>
										</div>
									</button>
								{/if}
								{#if page.data?.featureflags?.advanced_analytics && !page.data.user.is_third_party}
									<Anchor
										breadcrumbAction="push"
										href={`${page.url.pathname}/advanced-analytics`}
										class="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
										data-testid="advanced-analytics-button"
									>
										<div
											class="flex items-center justify-center w-8 h-8 rounded-lg bg-orange-500 text-white shrink-0"
										>
											<i class="fa-solid fa-chart-line text-sm"></i>
										</div>
										<span class="text-sm font-semibold">{m.advancedAnalytics()}</span>
									</Anchor>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg">
		<div class="flex flex-row items-center font-semibold justify-between">
			<div>
				<span class="h4">{m.associatedRequirements()}</span>
				<span class="badge bg-violet-400 text-white ml-1 rounded-xl">
					{#if treeViewNodes}
						{assessableNodesCount(treeViewNodes)}
					{/if}
				</span>
			</div>
			<Popover
				open={filterPopupOpen}
				onOpenChange={(e) => (filterPopupOpen = e.open)}
				positioning={{ placement: 'bottom-start' }}
				autoFocus={false}
				onPointerDownOutside={() => (filterPopupOpen = false)}
				closeOnInteractOutside={false}
			>
				<Popover.Trigger class="btn preset-filled-primary-500 w-fit">
					<i class="fa-solid fa-filter mr-2"></i>
					{m.filters()}
					{#if filterCount}
						<span class="text-xs">{filterCount}</span>
					{/if}
				</Popover.Trigger>
				<Popover.Positioner>
					<Popover.Content
						class="card p-2 bg-white w-fit shadow-lg space-y-2 border border-surface-200 z-10"
					>
						<div>
							<span class="text-sm font-bold">{m.result()}</span>
							<div class="flex flex-wrap gap-2 text-xs bg-gray-100 border-2 p-1 rounded-md">
								{#each Object.entries(complianceResultColorMap) as [result, color]}
									<button
										type="button"
										onclick={() => toggleResult(result)}
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
						{#if data.compliance_assessment.progress_status_enabled}
							<div>
								<span class="text-sm font-bold">{m.status()}</span>
								<div class="flex flex-wrap w-fit gap-2 text-xs bg-gray-100 border-2 p-1 rounded-md">
									{#each Object.entries(complianceStatusColorMap) as [status, color]}
										<button
											type="button"
											onclick={() => toggleStatus(status)}
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
						{/if}
						{#if data.compliance_assessment.extended_result_enabled}
							<div>
								<span class="text-sm font-bold">{m.extendedResult()}</span>
								<div class="flex flex-wrap w-fit gap-2 text-xs bg-gray-100 border-2 p-1 rounded-md">
									{#each Object.entries(extendedResultColorMap) as [extendedResult, color]}
										<button
											type="button"
											onclick={() => toggleExtendedResult(extendedResult)}
											class="px-2 py-1 rounded-md font-bold"
											style="background-color: {selectedExtendedResults.includes(extendedResult)
												? color
												: 'grey'}; color: white; opacity: {selectedExtendedResults.includes(
												extendedResult
											)
												? 1
												: 0.3};"
										>
											{safeTranslate(extendedResult)}
										</button>
									{/each}
								</div>
							</div>
						{/if}
						<div>
							<span class="text-sm font-bold">{m.ShowOnlyAssessable()}</span>
							<div id="toggle" class="flex items-center space-x-4 text-xs ml-auto mr-4">
								<Switch
									name="questionnaireToggle"
									class="flex flex-row items-center justify-center"
									checked={displayOnlyAssessableNodes}
									onCheckedChange={(e) => {
										displayOnlyAssessableNodes = e.checked;
										auditFiltersStore.setDisplayOnlyAssessableNodes(id, e.checked);
									}}
								>
									<Switch.Control>
										<Switch.Thumb />
									</Switch.Control>
									<Switch.HiddenInput />
									{#if displayOnlyAssessableNodes}
										<span class="font-bold text-xs text-primary-500">{m.yes()}</span>
									{:else}
										<span class="font-bold text-xs text-gray-500">{m.no()}</span>
									{/if}
								</Switch>
							</div>
						</div>
					</Popover.Content>
				</Popover.Positioner>
			</Popover>
		</div>

		<div class="flex items-center my-2 text-xs space-x-2 text-gray-500">
			<i class="fa-solid fa-diagram-project"></i>
			<p>{m.mappingInferenceTip()}</p>
		</div>
		{#key data}
			{#key displayOnlyAssessableNodes || selectedStatus || selectedResults || selectedExtendedResults}
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
		onclose={() => (threatDialogOpen = false)}
	>
		<div class="flex justify-between items-center mb-4">
			<h3 class="h3 font-bold capitalize">{m.potentialThreats()}</h3>
			<button class="btn btn-sm preset-filled-error-500" onclick={closeThreatsDialog}>
				<i class="fa-solid fa-times"></i>
			</button>
		</div>

		<div class="threats-content">
			<ForceCirclePacking data={data.threats.graph} name="threats_graph" height="h-[600px]" />
		</div>
	</dialog>
{/if}
