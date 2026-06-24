<script lang="ts">
	import type { SuperForm } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import BackgroundCheckbox from '$lib/components/Forms/BackgroundCheckbox.svelte';
	import { page } from '$app/state';

	interface Props {
		form: SuperForm<Record<string, boolean | undefined>>;
	}

	let { form }: Props = $props();

	const { form: formData } = form;

	const availableKeys: string[] = Object.keys(page.data.featureFlagSettings ?? {});

	const featureFlagGroups = [
		{
			category: m.organization(),
			description: m.organisationDescription(),
			fields: [
				{
					field: 'organisation_objectives',
					label: m.organisationObjectives(),
					description: m.organisationObjectivesDescription()
				},
				{
					field: 'organisation_issues',
					label: m.organisationIssues(),
					description: m.organisationIssuesDescription()
				},
				{
					field: 'journeys',
					label: m.journeys(),
					description: m.journeysDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.catalog(),
			description: m.CatalogDescription(),
			fields: [
				{
					field: 'security_advisories',
					label: m.securityAdvisories(),
					description: m.securityAdvisoriesDescription()
				},
				{
					field: 'cwes',
					label: m.cwe(),
					description: m.cweDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.operations(),
			description: m.operationsDescription(),
			fields: [
				{
					field: 'tasks',
					label: m.tasks(),
					description: m.taskTemplatesDescription()
				},
				{
					field: 'control_plan',
					label: m.tasksReview(),
					description: m.controlPlanDescription()
				},
				{
					field: 'xrays',
					label: m.xRays(),
					description: m.xRaysDescription()
				},
				{
					field: 'incidents',
					label: m.incidents(),
					description: m.incidentsDescription()
				},
				{
					field: 'follow_up',
					label: m.followUp(),
					description: m.findingsAssessmentsDescription()
				},
				{
					field: 'metrology',
					label: m.metrology(),
					description: m.metrologyDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.assetClassManagementAndGovernance(),
			description: m.assetClassManagementAndGovernanceDescription(),
			fields: [
				{
					field: 'project_management',
					label: m.projectManagement(),
					description: m.projectManagementDescription()
				},
				{
					field: 'reports',
					label: m.reports(),
					description: m.reportsDescription()
				},
				{
					field: 'tprm',
					label: m.thirdParty(),
					description: m.thirdPartyDescription()
				},
				{
					field: 'contracts',
					label: m.contracts(),
					description: m.contractsDescription()
				},
				{
					field: 'validation_flows',
					label: m.validationFlows(),
					description: m.validationFlowsDescription()
				},
				{
					field: 'policy_documents',
					label: m.policyDocumentsFlag(),
					description: m.policyDocumentsFlagDescription()
				},
				{
					field: 'exceptions',
					label: m.securityExceptions(),
					description: m.securityExceptionsDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.compliance(),
			description: m.complianceDescription(),
			fields: [
				{
					field: 'compliance',
					label: m.compliance(),
					description: m.complianceAssessmentsDescription()
				},
				{
					field: 'campaigns',
					label: m.campaigns(),
					description: m.campaignsDescription()
				},
				{
					field: 'auditee_mode',
					label: m.auditeeMode(),
					description: m.auditeeModeDescription()
				},
				{
					field: 'advanced_analytics',
					label: m.advancedAnalytics(),
					description: m.advancedAnalyticsDescription()
				},
				{
					field: 'audit_tree_inheritance',
					label: m.auditTreeInheritance(),
					description: m.auditTreeInheritanceDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.riskManagement(),
			description: m.riskManagementDescription(),
			fields: [
				{
					field: 'risk_acceptances',
					label: m.riskAcceptances(),
					description: m.riskAcceptancesDescription()
				},
				{
					field: 'inherent_risk',
					label: m.inherentRisk(),
					description: m.inherentRiskLevelHelpText()
				},
				{
					field: 'vulnerabilities',
					label: m.vulnerabilities(),
					description: m.vulnerabilitiesDescription()
				},
				{
					field: 'ebiosrm',
					label: m.ebiosRM(),
					description: m.ebiosRmDescription()
				},
				{
					field: 'quantitative_risk_studies',
					label: m.quantitativeRiskStudies(),
					description: m.quantitativeRiskStudiesDescription()
				},
				{
					field: 'scoring_assistant',
					label: m.scoringAssistant(),
					description: m.scoringAssistantDescription()
				},
				{
					field: 'bia',
					label: m.businessImpactAnalysis(),
					description: m.businessImpactAnalysisDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.gdpr(),
			description: m.gdprDescription(),
			fields: [
				{
					field: 'privacy',
					label: m.privacy(),
					description: m.privacyDescription()
				},
				{
					field: 'personal_data',
					label: m.personalData(),
					description: m.personalDataDescription()
				},
				{
					field: 'purposes',
					label: m.purposes(),
					description: m.purposesDescription()
				},
				{
					field: 'right_requests',
					label: m.rightRequests(),
					description: m.rightRequestsDescription()
				},
				{
					field: 'data_breaches',
					label: m.dataBreaches(),
					description: m.dataBreachesDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.extra(),
			description: m.extraDescription(),
			fields: [
				{
					field: 'focus_mode',
					label: m.focusMode(),
					description: m.focusModeTooltip()
				},
				{
					field: 'terminologies',
					label: m.terminologies(),
					description: m.riskOriginHelpText()
				},
				{
					field: 'custom_fields',
					label: m.customFields(),
					description: m.customFieldsDescription()
				},
				{
					field: 'outgoing_webhooks',
					label: m.webhooks(),
					description: m.webhooksDescription()
				},
				{
					field: 'audit_log_forwarding',
					label: m.auditLogForwarding(),
					description: m.auditLogForwardingDescription()
				},
				{
					field: 'comments',
					label: m.comments(),
					description: m.commentsDescription()
				},
				{
					field: 'experimental',
					label: m.experimental(),
					description: m.experimentalFeatures()
				},
				{
					field: 'chat_mode',
					label: m.chatMode(),
					description: m.chatModeDescription()
				},
				{
					field: 'object_audit_trail',
					label: m.objectAuditTrail(),
					description: m.objectAuditTrailDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		}
	].filter((group) => group.fields.length > 0);

	const allFields: string[] = featureFlagGroups.flatMap((g) => g.fields.map((f) => f.field));

	// Preset ON-sets. Any flag not listed is turned OFF when the preset is applied.
	// `inherent_risk` is intentionally absent from every preset (kept off by default).
	const PRESETS = [
		{
			id: 'minimal',
			label: m.presetMinimal(),
			description: m.presetMinimalDescription(),
			on: new Set(['compliance', 'tasks', 'control_plan', 'terminologies', 'comments'])
		},
		{
			id: 'compliance',
			label: m.presetComplianceFocused(),
			description: m.presetComplianceFocusedDescription(),
			on: new Set([
				'compliance',
				'tasks',
				'control_plan',
				'follow_up',
				'reports',
				'policy_documents',
				'advanced_analytics',
				'auditee_mode',
				'campaigns',
				'audit_tree_inheritance',
				'validation_flows',
				'security_advisories',
				'cwes',
				'metrology',
				'terminologies',
				'comments',
				'journeys',
				'organisation_objectives',
				'organisation_issues',
				'xrays'
			])
		},
		{
			id: 'risk',
			label: m.presetRiskFocused(),
			description: m.presetRiskFocusedDescription(),
			on: new Set([
				'compliance',
				'risk_acceptances',
				'exceptions',
				'vulnerabilities',
				'ebiosrm',
				'quantitative_risk_studies',
				'scoring_assistant',
				'bia',
				'follow_up',
				'tasks',
				'control_plan',
				'advanced_analytics',
				'reports',
				'security_advisories',
				'cwes',
				'metrology',
				'terminologies',
				'comments',
				'organisation_objectives',
				'organisation_issues',
				'xrays'
			])
		}
	];

	let query = $state('');

	const normalizedQuery = $derived(query.trim().toLowerCase());

	const filteredGroups = $derived(
		normalizedQuery === ''
			? featureFlagGroups
			: featureFlagGroups
					.map((group) => ({
						...group,
						fields: group.fields.filter(
							({ label, description }) =>
								label.toLowerCase().includes(normalizedQuery) ||
								(description ?? '').toLowerCase().includes(normalizedQuery)
						)
					}))
					.filter((group) => group.fields.length > 0)
	);

	const enabledCount = $derived(allFields.filter((f) => $formData[f]).length);

	function setFields(fields: string[], value: boolean) {
		formData.update((data) => {
			const next = { ...data };
			for (const f of fields) next[f] = value;
			return next;
		});
	}

	function applyPreset(on: Set<string>) {
		formData.update((data) => {
			const next = { ...data };
			for (const f of allFields) next[f] = on.has(f);
			return next;
		});
	}

	function resetToDefaults() {
		const defaults = (page.data.featureFlagDefaults ?? {}) as Record<string, boolean>;
		formData.update((data) => {
			const next = { ...data };
			for (const f of allFields) {
				if (f in defaults) next[f] = defaults[f];
			}
			return next;
		});
	}
</script>

<div class="space-y-6">
	<!-- Bulk-action toolbar -->
	<div
		class="sticky top-0 z-10 bg-surface-50-950/95 backdrop-blur rounded-xl border border-surface-200-800 shadow-sm p-4 flex flex-wrap items-center gap-3"
	>
		<div class="relative grow min-w-[200px] max-w-sm">
			<i
				class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-400-600"
			></i>
			<input
				type="text"
				bind:value={query}
				placeholder={m.searchPlaceholder()}
				class="w-full pl-9 pr-3 py-2 border border-surface-300-700 bg-surface-50-950 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
			/>
		</div>

		<span class="text-sm text-surface-600-400 whitespace-nowrap">
			{m.featureFlagsEnabledCount({ count: enabledCount, total: allFields.length })}
		</span>

		<div class="flex flex-wrap items-center gap-2 ml-auto">
			<button
				type="button"
				class="btn btn-sm variant-soft-primary"
				onclick={() => setFields(allFields, true)}
			>
				<i class="fa-solid fa-check-double mr-1"></i>{m.enableAll()}
			</button>
			<button
				type="button"
				class="btn btn-sm variant-soft"
				onclick={() => setFields(allFields, false)}
			>
				<i class="fa-solid fa-xmark mr-1"></i>{m.disableAll()}
			</button>
			<button type="button" class="btn btn-sm variant-soft" onclick={resetToDefaults}>
				<i class="fa-solid fa-rotate-left mr-1"></i>{m.resetToDefaults()}
			</button>

			<span class="border-l border-surface-300-700 h-6 mx-1"></span>

			<span class="text-sm font-medium text-surface-600-400">{m.featureFlagPresets()}:</span>
			{#each PRESETS as preset}
				<button
					type="button"
					class="btn btn-sm variant-ghost-primary"
					title={preset.description}
					onclick={() => applyPreset(preset.on)}
				>
					{preset.label}
				</button>
			{/each}
		</div>
	</div>

	{#if filteredGroups.length === 0}
		<div class="text-center text-surface-600-400 py-12">{m.noFeatureFlagsMatch()}</div>
	{/if}

	{#each filteredGroups as group (group.category)}
		{@const groupFields = group.fields.map((f) => f.field)}
		{@const groupEnabled = groupFields.filter((f) => $formData[f]).length}
		<div class="bg-surface-50-950 shadow-sm rounded-xl p-6 border border-surface-200-800">
			<div class="mb-4 flex items-start justify-between gap-4">
				<div>
					<h2 class="text-xl font-bold text-surface-950-50">{group.category}</h2>
					<p class="text-sm text-surface-600-400 mt-1">{group.description}</p>
				</div>
				<div class="flex items-center gap-2 shrink-0">
					<span class="text-xs text-surface-600-400 whitespace-nowrap"
						>{groupEnabled}/{groupFields.length}</span
					>
					<button
						type="button"
						class="btn btn-sm variant-soft-primary"
						title={m.enableAll()}
						onclick={() => setFields(groupFields, true)}
					>
						<i class="fa-solid fa-check"></i>
					</button>
					<button
						type="button"
						class="btn btn-sm variant-soft"
						title={m.disableAll()}
						onclick={() => setFields(groupFields, false)}
					>
						<i class="fa-solid fa-xmark"></i>
					</button>
				</div>
			</div>
			<div
				class="grid gap-4"
				style="grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); grid-auto-rows: 1fr;"
			>
				{#each group.fields as { field, label, description } (field)}
					<BackgroundCheckbox
						{form}
						{field}
						{label}
						helpText={description}
						classesContainer="h-full"
						classes="h-full"
					/>
				{/each}
			</div>
		</div>
	{/each}
</div>
