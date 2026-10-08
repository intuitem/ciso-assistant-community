<script lang="ts">
	import { ruleLabel } from '$lib/components/QuickForms/rule-label';
	import { run } from 'svelte/legacy';

	import { page } from '$app/state';
	import RecursiveTreeView, {
		setContextRecursiveTreeView,
		DEFAULT_CONTEXT_RECURSIVE_TREE_VIEW
	} from '$lib/components/TreeView/RecursiveTreeView.svelte';

	import { onMount } from 'svelte';

	import type { TreeViewNode } from '$lib/components/TreeView/types';

	import { Switch, Progress, Popover, Tooltip } from '@skeletonlabs/skeleton-svelte';

	import { goto, invalidateAll } from '$app/navigation';

	import type { ActionData, PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';

	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import AuditTrailButton from '$lib/components/AuditTrail/AuditTrailButton.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ExportModal, {
		type ExportFormat,
		type ExportGroup
	} from '$lib/components/Modals/ExportModal.svelte';

	import {
		complianceResultColorMap,
		complianceStatusColorMap,
		extendedResultColorMap
	} from '$lib/utils/constants';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RingProgress from '$lib/components/DataViz/RingProgress.svelte';
	import { URL_MODEL_MAP, getModelInfo, getMarkdownFields } from '$lib/utils/crud';
	import type { Node } from './types';

	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';

	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import SuggestControlsModal from '$lib/components/Modals/SuggestControlsModal.svelte';
	import {
		displayScoreColor,
		darkenColor,
		getScoreHexColor,
		getFieldVisibility
	} from '$lib/utils/helpers';
	import { auditFiltersStore, expandedNodesState } from '$lib/utils/stores';
	import TreeExpandCollapseToggle from '$lib/components/TreeView/TreeExpandCollapseToggle.svelte';
	import ExcludeNotApplicableRequirements from '$lib/components/TreeView/ExcludeNotApplicableRequirements.svelte';

	import { derived } from 'svelte/store';
	import { canPerformActionOnObject } from '$lib/utils/access-control';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import ValidationFlowsSection from '$lib/components/ValidationFlows/ValidationFlowsSection.svelte';
	import { countMasked, isMaskedPlaceholder } from '$lib/utils/related-visibility';

	const ISO27001_FRAMEWORK_URN_PREFIX = 'urn:intuitem:risk:framework:iso27001';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const scoreFloor = $derived(
		data.global_score?.score_calculation_method === 'sum' ? 0 : (data.global_score?.min_score ?? 0)
	);

	const compliance_assessment = $derived(data.compliance_assessment);

	const user = page.data.user;
	const model = URL_MODEL_MAP['compliance-assessments'];
	const markdownFields = getMarkdownFields('compliance-assessments');
	const canEditObject: boolean = canPerformActionOnObject({
		user,
		action: 'change',
		model: model.name,
		object: compliance_assessment
	});
	// Assignments that have actually been sent out: a draft has nothing to review yet.
	const activeAssignments = $derived(
		(compliance_assessment.requirement_assignments ?? []).filter(
			(a: { status?: string }) => a.status && a.status !== 'draft'
		)
	);
	const reviewResponsesHref = $derived(
		activeAssignments.length === 1
			? `/auditee-assessments/${activeAssignments[0].id}`
			: `${page.url.pathname}/assignments`
	);

	const requirementAssessmentModel = URL_MODEL_MAP['requirement-assessments'];
	const canEditRequirementAssessment: boolean =
		!data.compliance_assessment.is_locked &&
		canPerformActionOnObject({
			user,
			action: 'change',
			model: requirementAssessmentModel.name,
			object: data.compliance_assessment
		});

	const viewerRole: 'auditor' | 'respondent' = page.data.user.is_third_party
		? 'respondent'
		: 'auditor';
	const fieldVis = $derived(getFieldVisibility(compliance_assessment, viewerRole));
	const showAnswers = $derived(fieldVis.showAnswers);
	const showResult = $derived(fieldVis.showResult);
	const showExtendedResult = $derived(fieldVis.showExtendedResult);
	const showStatus = $derived(fieldVis.showStatus);
	const showScore = $derived(fieldVis.showScore);

	const outcomeRules = $derived(
		(compliance_assessment.outcome_rules ?? []) as Record<string, any>[]
	);
	// Verdicts follow the result's visibility, computed numbers the score's.
	const shownRules = $derived(
		outcomeRules.filter((rule) =>
			rule.kind === 'number'
				? showScore &&
					(rule.annotation || rule.label) &&
					compliance_assessment.computed_values?.[rule.ref_id] != null
				: showResult
		)
	);
	const outcomeMet = (rule: Record<string, any>) =>
		!!compliance_assessment.computed_outcome &&
		rule.ref_id in compliance_assessment.computed_outcome;

	// One column per implementation-group scope, in rule order; rules without
	// a scope get a column of their own, titled only when there are others.
	const outcomeColumns = $derived.by(() => {
		const definitions = (compliance_assessment.framework.implementation_groups_definition ??
			[]) as Record<string, any>[];
		const groupName = (id: string) => {
			const group = definitions.find((g) => g.ref_id === id);
			return group?.translations?.[getLocale()]?.name || group?.name || id;
		};
		const columns = new Map<string, { key: string; title: string; rules: Record<string, any>[] }>();
		for (const rule of shownRules) {
			const ids: string[] = rule.implementation_groups ?? [];
			const key = ids.join(',');
			if (!columns.has(key)) {
				columns.set(key, { key, title: ids.map(groupName).join(', '), rules: [] });
			}
			columns.get(key)!.rules.push(rule);
		}
		const list = [...columns.values()];
		const general = columns.get('');
		if (general && list.length > 1) general.title = m.general();
		return list;
	});
	const showVerdicts = $derived(outcomeColumns.length > 0);
	const verdictCount = $derived(shownRules.filter((rule) => rule.kind !== 'number').length);
	const verdictsMet = $derived(
		shownRules.filter((rule) => rule.kind !== 'number' && outcomeMet(rule)).length
	);

	const has_threats = data.threats.total_unique_threats > 0;

	const objectsNotVisibleLabel = (count: number): string => {
		return m.objectsNotVisible({ count });
	};

	let verdictsDialogOpen = $state(false);
	let verdictsDialog: HTMLDialogElement | undefined = $state();

	function openVerdictsDialog() {
		verdictsDialogOpen = true;
		setTimeout(() => verdictsDialog?.showModal(), 0);
	}

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
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import CompareAuditModal from '$lib/components/Modals/CompareAuditModal.svelte';
	import MapFromAuditModal from '$lib/components/Modals/MapFromAuditModal.svelte';
	import MappingDirectionModal from '$lib/components/Modals/MappingDirectionModal.svelte';

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
	let selectedControlCoverage = $state([]);
	let selectedEvidenceCoverage = $state([]);
	let displayOnlyAssessableNodes = $state(false);
	$effect(
		() =>
			({
				selectedStatus = [],
				selectedResults = [],
				selectedExtendedResults = [],
				selectedControlCoverage = [],
				selectedEvidenceCoverage = [],
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

	function toggleControlCoverage(coverage) {
		selectedControlCoverage = toggleItem(coverage, selectedControlCoverage);
		auditFiltersStore.setControlCoverage(page.params.id, selectedControlCoverage);
	}

	function toggleEvidenceCoverage(coverage) {
		selectedEvidenceCoverage = toggleItem(coverage, selectedEvidenceCoverage);
		auditFiltersStore.setEvidenceCoverage(page.params.id, selectedEvidenceCoverage);
	}

	function isNodeHidden(node: Node, displayOnlyAssessableNodes: boolean): boolean {
		const hasAssessableChildren = Object.keys(node.children || {}).length > 0;
		const controlCoverage = node.has_applied_controls ? 'with' : 'without';
		const evidenceCoverage = node.has_evidence ? 'with' : 'without';
		return (
			(displayOnlyAssessableNodes && !node.assessable && !hasAssessableChildren) ||
			(node.assessable &&
				((selectedStatus.length > 0 && !selectedStatus.includes(node.status)) ||
					(selectedResults.length > 0 && !selectedResults.includes(node.result)) ||
					(selectedExtendedResults.length > 0 &&
						!selectedExtendedResults.includes(node.extended_result)) ||
					(selectedControlCoverage.length > 0 &&
						!selectedControlCoverage.includes(controlCoverage)) ||
					(selectedEvidenceCoverage.length > 0 &&
						!selectedEvidenceCoverage.includes(evidenceCoverage))))
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
					showAnswers,
					showResult,
					showStatus,
					showScore,
					showDocumentationScore: data.compliance_assessment.show_documentation_score,
					showExtendedResult,
					scoringEnabled: data.compliance_assessment.scoring_enabled,
					scoreCalculationMethod: data.compliance_assessment.score_calculation_method,
					hidden,
					selectedStatus
				},
				children: node.children ? transformToTreeView(Object.entries(node.children), true) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[] | undefined = $state();

	function assessableNodesCount(nodes: TreeViewNode[], onlyVisible = false): number {
		let count = 0;
		for (const node of nodes) {
			if (node.contentProps?.assessable && !(onlyVisible && node.contentProps?.hidden)) {
				count++;
			}
			if (node.children) {
				count += assessableNodesCount(node.children, onlyVisible);
			}
		}
		return count;
	}

	let expandedNodes: string[] = $state([]);

	const contextTreeView = $state(structuredClone(DEFAULT_CONTEXT_RECURSIVE_TREE_VIEW));
	setContextRecursiveTreeView(contextTreeView);

	expandedNodes = $expandedNodesState;

	const modalStore: ModalStore = getModalStore();

	function modalApplyMapping(): void {
		// Entry point: let the user pick the mapping direction.
		// "Map to a framework" creates a new audit; "Map from an audit"
		// updates the current one.
		const modalComponent: ModalComponent = {
			ref: MappingDirectionModal,
			props: {
				mapTo: modalCreateForm,
				mapFrom: modalMapFromAudit
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent
		};
		modalStore.trigger(modal);
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

	function modalMapFromAudit(): void {
		const modalComponent: ModalComponent = {
			ref: MapFromAuditModal,
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

	function buildExportGroups(): ExportGroup[] {
		const ca = data.compliance_assessment;
		const id = ca.id;
		const isInternal = !page.data.user.is_third_party;
		const frameworkUrn = ca.framework?.urn ?? '';
		// Framework-specific exports (e.g. a publisher's official self-assessment
		// template) come from the backend, which knows which audits support them.
		// ISO27001 is prefix-matched — SoA only navigates to a page whose
		// semantics carry across 27001 versions.
		const frameworkExports: {
			ref_id: string;
			title: string;
			description: string;
			format: ExportFormat;
		}[] = ca.framework_exports ?? [];
		const isIso27001 = frameworkUrn.startsWith(ISO27001_FRAMEWORK_URN_PREFIX);

		const auditOptions = [
			isInternal && {
				titleKey: 'exportRequirementsData',
				descriptionKey: 'exportRequirementsDataDesc',
				format: 'CSV' as const,
				href: `/compliance-assessments/${id}/export/csv`,
				testId: 'export-option-csv'
			},
			isInternal && {
				titleKey: 'exportRequirementsWorkbook',
				descriptionKey: 'exportRequirementsWorkbookDesc',
				format: 'XLSX' as const,
				href: `/compliance-assessments/${id}/export/xlsx`,
				testId: 'export-option-xlsx'
			},
			isInternal && {
				titleKey: 'exportExecutiveSummary',
				descriptionKey: 'exportExecutiveSummaryDesc',
				format: 'DOCX' as const,
				href: `/compliance-assessments/${id}/export/word`,
				testId: 'export-option-word'
			},
			// Offered to third parties too: the backend redacts per viewer role.
			{
				titleKey: 'exportAuditPosture',
				descriptionKey: 'exportAuditPostureDesc',
				format: 'PDF' as const,
				href: `/compliance-assessments/${id}/export/posture-pdf?profile=full`,
				testId: 'export-option-posture-pdf'
			},
			{
				titleKey: 'exportAuditAttestation',
				descriptionKey: 'exportAuditAttestationDesc',
				format: 'PDF' as const,
				href: `/compliance-assessments/${id}/export/posture-pdf?profile=attestation`,
				testId: 'export-option-attestation-pdf'
			},
			...(isInternal
				? frameworkExports.map((frameworkExport) => ({
						titleKey: frameworkExport.title,
						descriptionKey: frameworkExport.description,
						format: frameworkExport.format,
						href: `/compliance-assessments/${id}/export/framework/${frameworkExport.ref_id}`,
						testId: `export-option-${frameworkExport.ref_id}`
					}))
				: []),
			{
				titleKey: 'exportBundleWithEvidences',
				descriptionKey: 'exportBundleWithEvidencesDesc',
				format: 'ZIP' as const,
				href: `/compliance-assessments/${id}/export`,
				testId: 'export-option-zip'
			},
			isInternal &&
				isIso27001 && {
					titleKey: 'exportSoaBuilder',
					descriptionKey: 'exportSoaBuilderDesc',
					format: 'HTML' as const,
					href: `/reports/soa?ca=${id}`,
					kind: 'navigate' as const,
					testId: 'export-option-soa'
				}
		].filter(Boolean);

		const actionPlanOptions = isInternal
			? [
					{
						titleKey: 'exportControlsList',
						descriptionKey: 'exportControlsListDesc',
						format: 'CSV' as const,
						href: `/compliance-assessments/${id}/action-plan/export/csv`,
						testId: 'export-option-ap-csv'
					},
					{
						titleKey: 'exportControlsWorkbook',
						descriptionKey: 'exportControlsWorkbookDesc',
						format: 'XLSX' as const,
						href: `/compliance-assessments/${id}/action-plan/export/xlsx`,
						testId: 'export-option-ap-xlsx'
					},
					{
						titleKey: 'exportStatusGroupedReport',
						descriptionKey: 'exportStatusGroupedReportDesc',
						format: 'PDF' as const,
						href: `/compliance-assessments/${id}/action-plan/export/pdf`,
						testId: 'export-option-ap-pdf'
					}
				]
			: [];

		return [
			{ titleKey: 'complianceAssessment', options: auditOptions as ExportGroup['options'] },
			{ titleKey: 'actionPlan', options: actionPlanOptions }
		];
	}

	function modalExport(): void {
		const modalComponent: ModalComponent = {
			ref: ExportModal,
			props: {
				title: m.exportOptionsTitle(),
				groups: buildExportGroups()
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
				URLModel: 'compliance-assessments',
				formAction: action,
				bodyComponent: List,
				bodyProps: {
					items: Object.values(requirementAssessmentsSync.changes).map(
						({ str, changes }) =>
							`${str}: ${changes
								.map((change) => `${safeTranslate(change.current)} ➡️ ${safeTranslate(change.new)}`)
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
			body: m.syncToAppliedControlsMessage(),
			response: (r: boolean) => {
				syncingToActionsIsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}
	let createAppliedControlsLoading = $state(false);

	async function modalConfirmCreateSuggestedControls(id: string, _name: string, _action: string) {
		if (createAppliedControlsLoading) return;
		createAppliedControlsLoading = true;
		type PreviewItem = { id: string; label: string; status: 'create' | 'reuse' | 'linked' };
		let previewItems: PreviewItem[] = [];
		try {
			const previewResponse = await fetch(
				`/compliance-assessments/${id}/suggestions/applied-controls?dry_run=true`
			);
			if (previewResponse.ok) {
				const previewData: any[] = await previewResponse.json();
				const seen = new Set<string>();
				previewItems = previewData
					.filter((control) => control?.reference_control?.id)
					.map((control) => ({
						id: control.reference_control.id as string,
						label:
							control?.name ||
							control?.reference_control?.str ||
							control?.reference_control?.name ||
							control?.ref_id ||
							'',
						status: (control?.suggestion_status as 'create' | 'reuse' | 'linked') ?? 'create'
					}))
					.filter((item) => {
						if (seen.has(item.id)) return false;
						seen.add(item.id);
						return true;
					});
			} else {
				throw new Error(await previewResponse.text());
			}
		} catch (error) {
			console.error('Unable to fetch suggested controls preview', error);
			previewItems = data.compliance_assessment.framework.reference_controls
				.filter((control: any) => control?.id)
				.map((control: any) => ({
					id: control.id as string,
					label:
						control?.name ||
						control?.reference_control?.str ||
						control?.reference_control?.name ||
						control?.ref_id ||
						'',
					status: 'create' as const
				}));
		}

		if (previewItems.length === 0) {
			createAppliedControlsLoading = false;
			return;
		}

		const modalComponent: ModalComponent = {
			ref: SuggestControlsModal,
			props: {
				items: previewItems,
				endpoint: `/compliance-assessments/${id}/suggestions/applied-controls`
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.suggestControls(),
			body: m.createAppliedControlsFromSuggestionsConfirmMessage({
				count: previewItems.filter((i) => i.status !== 'linked').length
			}),
			response: () => {
				createAppliedControlsLoading = false;
			}
		};
		modalStore.trigger(modal);
	}

	let tree = $derived(data.tree);
	let compliance_assessment_donut_values = $derived(data.compliance_assessment_donut_values);
	const chartCount = $derived(
		[
			showScore && data.global_score && data.global_score.maturity_score >= 0,
			showResult,
			showExtendedResult && compliance_assessment_donut_values.extended_result?.values?.length > 0,
			showStatus
		].filter(Boolean).length
	);
	const chartColumns = $derived(Math.min(Math.max(chartCount, 1), 2));
	// Two rows fill the header's height; a single row keeps its own and is centred.
	const chartRows = $derived(chartCount > 2 ? 'minmax(14rem, 1fr)' : 'minmax(18rem, auto)');

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
			(selectedControlCoverage.length > 0 ? 1 : 0) +
			(selectedEvidenceCoverage.length > 0 ? 1 : 0) +
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

	<div class="flex flex-col card px-6 py-4 bg-surface-50-950 shadow-lg w-full">
		<div class="flex flex-row justify-between">
			<div class="flex flex-col space-y-2 whitespace-pre-line w-1/5 pr-1">
				{#each Object.entries(data.compliance_assessment).filter(([key, value]) => {
					const fieldsToShow = ['ref_id', 'name', 'description', 'observation', 'version', 'folder', 'perimeter', 'framework', 'authors', 'reviewers', 'status', 'selected_implementation_groups', 'campaign'];
					if (!fieldsToShow.includes(key)) return false;
					if (value == null || value === '' || (Array.isArray(value) && value.length === 0)) return false;
					// Hide selected_implementation_groups if framework doesn't support implementation groups
					if (key === 'selected_implementation_groups' && (!data.compliance_assessment.framework.implementation_groups_definition || !Array.isArray(data.compliance_assessment.framework.implementation_groups_definition) || data.compliance_assessment.framework.implementation_groups_definition.length === 0)) return false;
					return true;
				}) as [key, value]}
					{@const isUpdatableFramework = key === 'framework' && value.has_update}
					<div class="flex flex-col">
						<div
							class="text-sm font-medium text-surface-800-200 capitalize-first"
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
								class="text-surface-600-400 list-none"
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
									{:else if markdownFields.has(key)}
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
			<div class="flex-1 min-w-0 flex flex-col gap-2">
				<div
					class="flex-1 grid gap-2"
					style="grid-template-columns: repeat({chartColumns}, minmax(0, 1fr)); grid-auto-rows: {chartRows}; align-content: {chartCount >
					2
						? 'stretch'
						: 'center'};"
				>
					{#key compliance_assessment_donut_values}
						{#if showScore && data.global_score && data.global_score.maturity_score >= 0}
							<div class="min-w-0 min-h-56">
								<RingProgress
									name="global_maturity"
									value={data.global_score.maturity_score}
									max={data.global_score.total_max_score}
									min={scoreFloor}
									color={getScoreHexColor(
										data.global_score.maturity_score,
										data.global_score.total_max_score,
										false,
										scoreFloor
									)}
									strokeWidth={35}
									fontSize={36}
									title={m.maturity()}
								/>
							</div>
						{/if}
						{#if showResult}
							<div class="min-w-0 min-h-56">
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
						{/if}
						{#if showExtendedResult && compliance_assessment_donut_values.extended_result?.values?.length > 0}
							<div class="min-w-0 min-h-56">
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
						{#if showStatus}
							<div class="min-w-0 min-h-56">
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
				</div>
				{#if showAnswers && data.compliance_assessment.answers_progress != null}
					<div class="flex items-center gap-2 text-sm text-surface-600-400">
						<i class="fa-solid fa-clipboard-question text-primary-500"></i>
						<span>{m.questions()}: {data.compliance_assessment.answers_progress}%</span>
						<div class="flex-1 bg-surface-200-800 rounded-full h-1.5 max-w-32">
							<div
								class="h-1.5 rounded-full bg-primary-400 transition-all"
								style="width: {data.compliance_assessment.answers_progress}%;"
							></div>
						</div>
					</div>
				{/if}
			</div>
			<div class="flex flex-col space-y-2 ml-4 w-80 xl:w-96 shrink-0">
				<div class="flex flex-row space-x-2">
					<button
						type="button"
						class="btn preset-filled-primary-500 w-full"
						onclick={modalExport}
						data-testid="export-button"
					>
						<i class="fa-solid fa-download mr-2"></i>{m.exportButton()}
					</button>
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
					{#each page.data?.featureflags?.findings_from_requirements ? (data.compliance_assessment.findings_assessments ?? []) : [] as binder}
						<Anchor
							href={`/findings-assessments/${binder.id}`}
							class="btn preset-filled-secondary-500 h-fit"
							breadcrumbAction="push"
							data-testid="go-to-findings-binder-button"
							><i class="fa-solid fa-bug mr-2"></i>{m.findings()}</Anchor
						>
					{/each}
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
					<AuditTrailButton
						model="compliance-assessments"
						objectId={data.compliance_assessment.id}
						folderId={data.compliance_assessment.folder?.id ?? user.root_folder_id}
					/>
				{/if}
				<!-- Power-ups Command Palette Grid -->
				<div class="pt-3 border-t border-surface-200-800 mt-2 space-y-3">
					<span
						class="text-xs font-semibold text-surface-400-600 uppercase tracking-widest select-none"
						>{m.powerUps()}</span
					>

					<!-- Modes -->
					<div>
						<span
							class="text-[11px] font-medium text-surface-400-600 uppercase tracking-wider mb-1.5 block"
							>{m.modes()}</span
						>
						<div class="grid grid-cols-2 gap-2">
							{#if !page.data.user.is_third_party}
								<Anchor
									breadcrumbAction="push"
									href={`${page.url.pathname}/flash-mode`}
									class="flex items-center gap-2 px-2.5 py-3 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-700 hover:bg-indigo-100 hover:border-indigo-200 dark:bg-surface-800 dark:border-surface-700 dark:text-indigo-300 dark:hover:bg-surface-700 dark:hover:border-surface-600 transition-colors cursor-pointer"
									data-testid="flash-mode-button"
								>
									<div
										class="flex items-center justify-center w-7 h-7 rounded-lg bg-indigo-500 dark:bg-indigo-600 text-white shrink-0"
									>
										<i class="fa-solid fa-bolt text-sm"></i>
									</div>
									<span class="text-sm font-semibold leading-tight">{m.flashMode()}</span>
								</Anchor>
							{/if}
							<Anchor
								breadcrumbAction="push"
								href={`${page.url.pathname}/table-mode`}
								class="flex items-center gap-2 px-2.5 py-3 rounded-xl bg-surface-50-950 border border-surface-100-900 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-200-800 transition-colors cursor-pointer"
								data-testid="table-mode-button"
							>
								<div
									class="flex items-center justify-center w-7 h-7 rounded-lg bg-slate-500 text-white shrink-0"
								>
									<i class="fa-solid fa-table-list text-sm"></i>
								</div>
								<span class="text-sm font-semibold leading-tight">{m.tableMode()}</span>
							</Anchor>
						</div>
					</div>

					<!-- Actions -->
					{#if !page.data.user.is_third_party}
						<div>
							<span
								class="text-[11px] font-medium text-surface-400-600 uppercase tracking-wider mb-1.5 block"
								>{m.actions()}</span
							>
							<div class="grid grid-cols-2 gap-2">
								<button
									class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
									onclick={() => modalApplyMapping()}
									data-testid="apply-mapping-button"
								>
									<i class="fa-solid fa-diagram-project text-emerald-500 text-base"></i>
									<span class="text-sm font-medium leading-tight">{m.applyMapping()}</span>
								</button>
								<button
									class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
									onclick={() => modalCreateCloneForm()}
									data-testid="clone-audit-button"
								>
									<i class="fa-solid fa-copy text-fuchsia-500 text-base"></i>
									<span class="text-sm font-medium leading-tight">{m.cloneAudit()}</span>
								</button>
								<button
									class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
									onclick={() => modalCompareAudit()}
									data-testid="compare-audit-button"
								>
									<i class="fa-solid fa-code-compare text-rose-500 text-base"></i>
									<span class="text-sm font-medium leading-tight">{m.compareToAudit()}</span>
								</button>
								{#if page.data?.featureflags?.validation_flows}
									<button
										class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
										onclick={() => modalRequestValidation()}
										data-testid="request-validation-button"
									>
										<i class="fa-solid fa-check-circle text-amber-500 text-base"></i>
										<span class="text-sm font-medium leading-tight">{m.requestValidation()}</span>
									</button>
								{/if}
								{#if !data.compliance_assessment.is_locked}
									<button
										class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
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
										<span class="text-sm font-medium leading-tight"
											>{m.syncToAppliedControls()}</span
										>
									</button>
									{#if canPerformActionOnObject( { user: page.data.user, action: 'add', model: 'appliedcontrol', object: data.compliance_assessment } ) && data.compliance_assessment.framework.reference_controls.length > 0}
										<button
											class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
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
											<span class="text-sm font-medium leading-tight">{m.suggestControls()}</span>
										</button>
									{/if}
								{/if}
								{#if canEditObject && page.data?.featureflags?.auditee_mode && !data.compliance_assessment.is_locked && data.compliance_assessment.status !== 'in_review'}
									<Anchor
										breadcrumbAction="push"
										href={`${page.url.pathname}/assignments`}
										class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
										data-testid="assignments-button"
									>
										<i class="fa-solid fa-user-tag text-green-500 text-base"></i>
										<span class="text-sm font-medium leading-tight">{m.assignments()}</span>
									</Anchor>
								{/if}
								{#if page.data?.featureflags?.auditee_mode && activeAssignments.length > 0}
									<!-- Reviewing what was answered was reachable only through the
										assignments page, which disappears once the audit is locked or in
										review — exactly when a reviewer needs it. -->
									<Anchor
										breadcrumbAction="push"
										href={reviewResponsesHref}
										class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border border-surface-200-800 bg-surface-50-950 text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 transition-colors shadow-sm cursor-pointer text-left"
										data-testid="review-responses-button"
									>
										<i class="fa-solid fa-clipboard-check text-blue-500 text-base"></i>
										<span class="text-sm font-medium leading-tight">{m.reviewResponses()}</span>
									</Anchor>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Insights -->
					{#if showVerdicts || ((has_threats || page.data?.featureflags?.advanced_analytics) && !page.data.user.is_third_party)}
						<div>
							<span
								class="text-[11px] font-medium text-surface-400-600 uppercase tracking-wider mb-1.5 block"
								>{m.insights()}</span
							>
							<div class="grid grid-cols-2 gap-2">
								{#if showVerdicts}
									{@const allMet = verdictCount > 0 && verdictsMet === verdictCount}
									<button
										type="button"
										class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl border transition-colors cursor-pointer text-left {allMet
											? 'bg-success-50-950 border-success-200-800 text-success-800-200 hover:bg-success-100-900'
											: 'bg-surface-50-950 border-surface-200-800 text-surface-700-300 hover:bg-surface-100-900'}"
										onclick={openVerdictsDialog}
										data-testid="verdicts-tile"
									>
										<div
											class="flex items-center justify-center w-7 h-7 rounded-lg text-white shrink-0 {allMet
												? 'bg-success-500 dark:bg-success-600'
												: 'bg-violet-500 dark:bg-violet-600'}"
										>
											<i class="fa-solid fa-scale-balanced text-sm"></i>
										</div>
										{#if verdictCount}
											<div class="flex flex-col">
												<span class="text-lg font-bold leading-tight tabular-nums"
													>{verdictsMet}<span class="text-sm font-medium opacity-70"
														>{` / ${verdictCount}`}</span
													></span
												>
												<span class="text-xs opacity-80"
													>{m.verdictsMet({ count: verdictCount })}</span
												>
											</div>
										{:else}
											<span class="text-sm font-semibold leading-tight">{m.computedOutcomes()}</span
											>
										{/if}
									</button>
								{/if}
								{#if has_threats && !page.data.user.is_third_party}
									<button
										class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 hover:bg-amber-100 transition-colors cursor-pointer text-left"
										onclick={openThreatsDialog}
									>
										<div
											class="flex items-center justify-center w-7 h-7 rounded-lg bg-amber-500 dark:bg-amber-600 text-white shrink-0"
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
										class="flex items-center gap-2 px-2.5 py-2.5 rounded-xl bg-surface-50-950 border border-surface-200-800 text-surface-700-300 hover:bg-surface-100-900 transition-colors cursor-pointer"
										data-testid="advanced-analytics-button"
									>
										<div
											class="flex items-center justify-center w-7 h-7 rounded-lg bg-orange-500 dark:bg-orange-600 text-white shrink-0"
										>
											<i class="fa-solid fa-chart-line text-sm"></i>
										</div>
										<span class="text-sm font-semibold leading-tight">{m.advancedAnalytics()}</span>
									</Anchor>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
	<div class="card px-6 py-4 bg-surface-50-950 flex flex-col shadow-lg">
		<div class="flex flex-row items-center font-semibold justify-between">
			<div>
				<span class="h4">{m.associatedRequirements()}</span>
				<span class="badge bg-violet-400 text-white ml-1 rounded-xl">
					{#if treeViewNodes}
						{#if filterCount}
							{assessableNodesCount(treeViewNodes, true)} / {assessableNodesCount(treeViewNodes)}
						{:else}
							{assessableNodesCount(treeViewNodes)}
						{/if}
					{/if}
				</span>
			</div>
			<div class="flex items-center gap-2">
				{#if treeViewNodes}
					<TreeExpandCollapseToggle nodes={treeViewNodes} bind:expandedNodes />
					<ExcludeNotApplicableRequirements
						bind:excludeNotApplicableRequirements={contextTreeView.excludeNotApplicableRequirements}
					/>
				{/if}
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
							class="card p-2 bg-surface-50-950 w-fit shadow-lg space-y-2 border border-surface-200 z-10"
						>
							{#if showResult}
								<div>
									<span class="text-sm font-bold">{m.result()}</span>
									<div
										class="flex flex-wrap gap-2 text-xs bg-surface-200-800 border-2 p-1 rounded-md"
									>
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
							{/if}
							{#if showStatus}
								<div>
									<span class="text-sm font-bold">{m.status()}</span>
									<div
										class="flex flex-wrap w-fit gap-2 text-xs bg-surface-200-800 border-2 p-1 rounded-md"
									>
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
							{#if showExtendedResult}
								<div>
									<span class="text-sm font-bold">{m.extendedResult()}</span>
									<div
										class="flex flex-wrap w-fit gap-2 text-xs bg-surface-200-800 border-2 p-1 rounded-md"
									>
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
								<span class="text-sm font-bold">{m.appliedControls()}</span>
								<div
									class="flex flex-wrap w-fit gap-2 text-xs bg-surface-200-800 border-2 p-1 rounded-md"
								>
									{#each ['with', 'without'] as coverage}
										<button
											type="button"
											onclick={() => toggleControlCoverage(coverage)}
											class="px-2 py-1 rounded-md font-bold {selectedControlCoverage.includes(
												coverage
											)
												? 'bg-primary-500 text-white'
												: 'bg-surface-400 text-black opacity-30'}"
										>
											{coverage === 'with' ? m.withAppliedControls() : m.withoutAppliedControls()}
										</button>
									{/each}
								</div>
							</div>
							<div>
								<span class="text-sm font-bold">{m.evidence()}</span>
								<span class="text-xs text-surface-600-400 ml-1">({m.evidenceCoverageHint()})</span>
								<div
									class="flex flex-wrap w-fit gap-2 text-xs bg-surface-200-800 border-2 p-1 rounded-md"
								>
									{#each ['with', 'without'] as coverage}
										<button
											type="button"
											onclick={() => toggleEvidenceCoverage(coverage)}
											class="px-2 py-1 rounded-md font-bold {selectedEvidenceCoverage.includes(
												coverage
											)
												? 'bg-primary-500 text-white'
												: 'bg-surface-400 text-black opacity-30'}"
										>
											{coverage === 'with' ? m.withEvidence() : m.withoutEvidence()}
										</button>
									{/each}
								</div>
							</div>
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
											<span class="font-bold text-xs text-surface-600-400">{m.no()}</span>
										{/if}
									</Switch>
								</div>
							</div>
						</Popover.Content>
					</Popover.Positioner>
				</Popover>
			</div>
		</div>

		<div class="flex items-center my-2 text-xs space-x-2 text-surface-600-400">
			<i class="fa-solid fa-diagram-project"></i>
			<p>{m.mappingInferenceTip()}</p>
		</div>
		{#key data}
			{#key [displayOnlyAssessableNodes, selectedStatus, selectedResults, selectedExtendedResults, selectedControlCoverage, selectedEvidenceCoverage].join('|')}
				<RecursiveTreeView
					nodes={transformToTreeView(Object.entries(tree))}
					bind:expandedNodes
					hover="hover:bg-initial"
				/>
			{/key}
		{/key}
	</div>
</div>
{#if verdictsDialogOpen}
	<dialog
		bind:this={verdictsDialog}
		class="fixed inset-0 m-auto w-[90vw] max-w-5xl max-h-[85vh] rounded-2xl bg-surface-50-950 shadow-2xl border border-surface-200-800 p-0 overflow-hidden backdrop:bg-black/40"
		aria-labelledby="verdicts-dialog-title"
		onclose={() => (verdictsDialogOpen = false)}
	>
		<div class="flex justify-between items-center px-6 py-4 border-b border-surface-100-900">
			<h3 id="verdicts-dialog-title" class="text-lg font-bold text-surface-900-100">
				{m.computedOutcomes()}
			</h3>
			<button
				class="flex items-center justify-center w-8 h-8 rounded-lg hover:bg-surface-200-800 transition-colors text-surface-600-400 hover:text-surface-700-300"
				aria-label={m.close()}
				onclick={() => verdictsDialog?.close()}
			>
				<i class="fa-solid fa-times"></i>
			</button>
		</div>
		<div class="p-4 max-h-[calc(85vh-64px)] overflow-auto">
			<div class="grid gap-3" style="grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));">
				{#each outcomeColumns as column (column.key)}
					{@const verdicts = column.rules.filter((rule) => rule.kind !== 'number')}
					{@const met = verdicts.filter((rule) => outcomeMet(rule)).length}
					<div class="rounded-lg border border-surface-200-800 bg-surface-50-950 p-3">
						{#if column.title}
							<div class="flex items-baseline justify-between gap-2 mb-2">
								<span
									class="text-xs font-semibold uppercase tracking-wide text-surface-600-400 truncate"
									>{column.title}</span
								>
								{#if verdicts.length}
									<span
										class="text-xs tabular-nums font-medium {met === verdicts.length
											? 'text-success-700-300'
											: 'text-surface-500'}">{met} / {verdicts.length}</span
									>
								{/if}
							</div>
						{/if}
						<ul class="space-y-1.5">
							{#each column.rules as rule (rule.ref_id)}
								{#if rule.kind === 'number'}
									<li class="flex items-baseline justify-between gap-3 text-sm">
										<span class="text-surface-700-300">{ruleLabel(rule, rule.ref_id)}</span>
										<span class="font-semibold tabular-nums"
											>{Number(compliance_assessment.computed_values[rule.ref_id]).toLocaleString(
												getLocale(),
												{ maximumFractionDigits: 2 }
											)}</span
										>
									</li>
								{:else}
									{@const isMet = outcomeMet(rule)}
									<li class="flex items-start gap-2 text-sm">
										<i
											class="{isMet
												? 'fa-solid fa-circle-check'
												: 'fa-regular fa-circle text-surface-400-600'} mt-0.5 shrink-0"
											style={isMet ? `color: ${rule.color ?? 'var(--color-success-500)'}` : ''}
											aria-hidden="true"
										></i>
										<span class={isMet ? 'text-surface-900-50 font-medium' : 'text-surface-600-400'}
											>{ruleLabel(rule, rule.ref_id)}<span class="sr-only"
												>: {isMet ? m.outcomeMet() : m.outcomeNotMet()}</span
											></span
										>
									</li>
								{/if}
							{/each}
						</ul>
					</div>
				{/each}
			</div>
		</div>
	</dialog>
{/if}
{#if threatDialogOpen}
	<dialog
		bind:this={dialogElement}
		class="fixed inset-0 m-auto w-[90vw] max-w-5xl h-[85vh] rounded-2xl bg-surface-50-950 shadow-2xl border border-surface-200-800 p-0 overflow-hidden backdrop:bg-black/40"
		aria-labelledby="threats-dialog-title"
		onclose={() => (threatDialogOpen = false)}
	>
		<div class="flex justify-between items-center px-6 py-4 border-b border-surface-100-900">
			<h3 id="threats-dialog-title" class="text-lg font-bold text-surface-900-100">
				{m.potentialThreats()}
			</h3>
			<button
				class="flex items-center justify-center w-8 h-8 rounded-lg hover:bg-surface-200-800 transition-colors text-surface-600-400 hover:text-surface-700-300"
				aria-label="Close"
				onclick={closeThreatsDialog}
			>
				<i class="fa-solid fa-times"></i>
			</button>
		</div>
		<div class="p-4 h-[calc(85vh-64px)] overflow-auto">
			<ForceCirclePacking
				data={data.threats.graph}
				name="threats_graph"
				height="h-[calc(85vh-120px)]"
			/>
		</div>
	</dialog>
{/if}
