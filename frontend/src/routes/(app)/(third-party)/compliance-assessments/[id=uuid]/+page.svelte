<script lang="ts">
	import { page } from '$app/stores';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import { breadcrumbObject } from '$lib/utils/stores';
	import type {
		ModalComponent,
		ModalSettings,
		ModalStore,
		PopupSettings,
		ToastStore,
		TreeViewNode
	} from '@skeletonlabs/skeleton';
	import { getModalStore, getToastStore, popup } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import TreeViewItemLead from './TreeViewItemLead.svelte';

	import CreateModal from '$lib/components/Modals/CreateModal.svelte';

	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import type { Node } from './types';

	import * as m from '$paraglide/messages';
	import { localItems, toCamelCase } from '$lib/utils/locales';

	export let data: PageData;
	breadcrumbObject.set(data.compliance_assessment);
	const tree = data.tree;

	const compliance_assessment_donut_values = data.compliance_assessment_donut_values;

	const user = $page.data.user;
	const model = URL_MODEL_MAP['compliance-assessments'];
	const canEditObject: boolean = Object.hasOwn(user.permissions, `change_${model.name}`);
	const requirementAssessmentModel = URL_MODEL_MAP['requirement-assessments'];
	const canEditRequirementAssessment: boolean = Object.hasOwn(
		user.permissions,
		`change_${requirementAssessmentModel.name}`
	);

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
			resultCounts['total_score'] = (resultCounts['total_score'] || 0) + node.score;
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

	function transformToTreeView(nodes: Node[]) {
		return nodes.map(([id, node]) => {
			node.resultCounts = countResults(node);
			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: { ...node, canEditRequirementAssessment },
				lead: TreeViewItemLead,
				leadProps: {
					statusI18n: node.status_i18n,
					resultI18n: node.result_i18n,
					assessable: node.assessable,
					statusColor: complianceStatusColorMap[node.status],
					resultColor: complianceResultColorMap[node.result],
					score: node.score,
					isScored: node.is_scored,
					max_score: node.max_score
				},
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[] = transformToTreeView(Object.entries(tree));

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

	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { expandedNodesState } from '$lib/utils/stores';
	import { displayScoreColor } from '$lib/utils/helpers';
	import { superForm } from 'sveltekit-superforms';

	expandedNodes = $expandedNodesState;
	$: expandedNodesState.set(expandedNodes);

	const popupDownload: PopupSettings = {
		event: 'click',
		target: 'popupDownload',
		placement: 'bottom'
	};

	const modalStore: ModalStore = getModalStore();
	const toastStore: ToastStore = getToastStore();

	function handleFormUpdated({
		form,
		pageStatus,
		closeModal
	}: {
		form: any;
		pageStatus: number;
		closeModal: boolean;
	}) {
		if (closeModal && form.valid) {
			$modalStore[0] ? modalStore.close() : null;
		}
		if (form.message) {
			const toast: { message: string; background: string } = {
				message: form.message,
				background: pageStatus === 200 ? 'variant-filled-success' : 'variant-filled-error'
			};
			toastStore.trigger(toast);
		}
	}

	let { form: createForm, message: createMessage } = {
		form: {},
		message: {}
	};

	$: {
		({ form: createForm, message: createMessage } = superForm(data.auditCreateForm, {
			onUpdated: ({ form }) =>
				handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
		}));
	}

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

	$: createAppliedControlsLoading = false;

	async function createAppliedControlsFromSuggestions() {
		createAppliedControlsLoading = true;
		const response = await fetch(
			`/compliance-assessments/${data.compliance_assessment.id}/suggestions/applied-controls`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			}
		);
		createAppliedControlsLoading = false;
		toastStore.trigger({
			message: response.ok
				? m.createAppliedControlsFromSuggestionsSuccess()
				: m.createAppliedControlsFromSuggestionsError(),
			background: response.ok ? 'variant-filled-success' : 'variant-filled-error'
		});
		return;
	}
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg w-full">
		<div class="flex flex-col space-y-2 whitespace-pre-line w-1/5 pr-1">
			{#each Object.entries(data.compliance_assessment).filter( ([key, _]) => ['name', 'description', 'project', 'framework', 'authors', 'reviewers', 'status', 'selected_implementation_groups'].includes(key) ) as [key, value]}
				<div class="flex flex-col">
					<div
						class="text-sm font-medium text-gray-800 capitalize-first"
						data-testid={key.replaceAll('_', '-') + '-field-title'}
					>
						{#if key === 'urn'}
							{m.urn()}
						{:else}
							{localItems()[toCamelCase(key)]}
						{/if}
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
														<a href={itemHref} class="anchor">{val.str}</a>
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
										<a href={itemHref} class="anchor">{value.str}</a>
									{:else}
										{value.str}
									{/if}
								{:else if localItems()[toCamelCase(value.str ?? value)]}
									{localItems()[toCamelCase(value.str ?? value)]}
								{:else}
									{value.str ?? value}
								{/if}
							{:else}
								--
							{/if}
						</li>
					</ul>
				</div>
			{/each}
		</div>
		{#if !$page.data.user.is_third_party}
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
		{/if}
		<div class="flex flex-col space-y-2 ml-4">
			{#if !$page.data.user.is_third_party}
				<div class="flex flex-row space-x-2">
					<button class="btn variant-filled-primary w-full" use:popup={popupDownload}
						><i class="fa-solid fa-download mr-2" />{m.exportButton()}</button
					>
					<div
						class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1 z-10"
						data-popup="popupDownload"
					>
						<p class="block px-4 py-2 text-sm text-gray-800">{m.complianceAssessment()}</p>

						<a
							href="/compliance-assessments/{data.compliance_assessment.id}/export/csv"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asCSV()}</a
						>
						<a
							href="/compliance-assessments/{data.compliance_assessment.id}/export"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asZIP()}</a
						>
						<p class="block px-4 py-2 text-sm text-gray-800">{m.actionPlan()}</p>
						<a
							href="/compliance-assessments/{data.compliance_assessment.id}/action-plan/export/pdf"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asPDF()}</a
						>
					</div>
					{#if canEditObject}
						<a
							href={`${$page.url.pathname}/edit?next=${$page.url.pathname}`}
							class="btn variant-filled-primary h-fit"
							data-testid="edit-button"><i class="fa-solid fa-pen-to-square mr-2" /> {m.edit()}</a
						>
					{/if}
				</div>
				<a href={`${$page.url.pathname}/action-plan`} class="btn variant-filled-primary h-fit"
					><i class="fa-solid fa-heart-pulse mr-2" />{m.actionPlan()}</a
				>
			{/if}
			<span class="pt-4 font-light text-sm">Power-ups:</span>
			{#if !$page.data.user.is_third_party}
				<a
					href={`${$page.url.pathname}/flash-mode`}
					class="btn text-gray-100 bg-gradient-to-l from-sky-500 to-violet-500 h-fit"
					><i class="fa-solid fa-bolt mr-2" /> {m.flashMode()}</a
				>
			{/if}
			<a
				href={`${$page.url.pathname}/table-mode`}
				class="btn text-gray-100 bg-gradient-to-l from-sky-500 to-yellow-500 h-fit"
				><i class="fa-solid fa-table-list mr-2" /> {m.tableMode()}</a
			>
			{#if !$page.data.user.is_third_party}
				<button
					class="btn text-gray-100 bg-gradient-to-l from-sky-500 to-green-600 h-fit"
					on:click={(_) => modalCreateForm()}
					><i class="fa-solid fa-diagram-project mr-2" /> {m.mapping()}
				</button>
			{/if}
			{#if Object.hasOwn($page.data.user.permissions, 'add_appliedcontrol')}
				<button
					class="btn text-gray-100 bg-gradient-to-l from-tertiary-400 to-orange-600 h-fit whitespace-normal"
					on:click={(_) => createAppliedControlsFromSuggestions()}
				>
					<span class="mr-2">
						{#if createAppliedControlsLoading}
							<ProgressRadial class="-ml-2" width="w-6" meter="stroke-white" stroke={80} />
						{:else}
							<i class="fa-solid fa-fire-extinguisher" />
						{/if}
					</span>
					{m.createAppliedControlsFromSuggestions()}
				</button>
			{/if}
		</div>
	</div>
	{#if !$page.data.user.is_third_party}
		<div class="card px-6 py-4 bg-white flex flex-col shadow-lg">
			<h4 class="h4 flex items-center font-semibold">
				{m.associatedRequirements()}
				<span class="badge variant-soft-primary ml-1">
					{assessableNodesCount(treeViewNodes)}
				</span>
			</h4>
			<div class="flex items-center my-2 text-xs space-x-2 text-gray-500">
				<i class="fa-solid fa-diagram-project" />
				<p>{m.mappingInferenceTip()}</p>
			</div>
			<RecursiveTreeView nodes={treeViewNodes} bind:expandedNodes hover="hover:bg-initial" />
		</div>
	{/if}
</div>
