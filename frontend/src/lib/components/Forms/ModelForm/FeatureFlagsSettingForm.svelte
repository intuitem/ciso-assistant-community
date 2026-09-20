<script lang="ts">
	import type { SuperForm } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import BackgroundCheckbox from '$lib/components/Forms/BackgroundCheckbox.svelte';
	import { page } from '$app/state';
	import { getFeatureFlagGroups } from '$lib/utils/feature-flag-groups';

	interface Props {
		form: SuperForm<Record<string, boolean | undefined>>;
	}

	let { form }: Props = $props();

	const { form: formData } = form;

	const availableKeys: string[] = Object.keys(page.data.featureFlagSettings ?? {});

	const featureFlagGroups = getFeatureFlagGroups(availableKeys);

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
				'document_management',
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
				class="btn btn-sm preset-tonal-primary"
				onclick={() => setFields(allFields, true)}
			>
				<i class="fa-solid fa-check-double mr-1"></i>{m.enableAll()}
			</button>
			<button
				type="button"
				class="btn btn-sm preset-tonal"
				onclick={() => setFields(allFields, false)}
			>
				<i class="fa-solid fa-xmark mr-1"></i>{m.disableAll()}
			</button>
			<button type="button" class="btn btn-sm preset-tonal" onclick={resetToDefaults}>
				<i class="fa-solid fa-rotate-left mr-1"></i>{m.resetToDefaults()}
			</button>

			<span class="border-l border-surface-300-700 h-6 mx-1"></span>

			<span class="text-sm font-medium text-surface-600-400">{m.featureFlagPresets()}:</span>
			{#each PRESETS as preset}
				<button
					type="button"
					class="btn btn-sm preset-outlined-primary-500"
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
						class="btn btn-sm preset-tonal-primary"
						title={m.enableAll()}
						onclick={() => setFields(groupFields, true)}
					>
						<i class="fa-solid fa-check"></i>
					</button>
					<button
						type="button"
						class="btn btn-sm preset-tonal"
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
