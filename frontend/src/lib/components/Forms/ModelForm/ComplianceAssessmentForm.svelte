<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages';
	import Checkbox from '../Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { page } from '$app/state';
	import FrameworkResultSnippet from '$lib/components/Snippets/AutocompleteSelect/FrameworkResultSnippet.svelte';
	import VisibilityEditor from '$lib/components/ComplianceAssessment/VisibilityEditor.svelte';
	import ScoreScaleEditor from '$lib/components/ComplianceAssessment/ScoreScaleEditor.svelte';
	import { scaleLevels, type ScoreScaleValue } from '$lib/utils/score-scales';
	import { untrack } from 'svelte';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		context: string;
	}

	let {
		form,
		model = $bindable(),
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context
	}: Props = $props();

	const formData = form.form;

	let suggestions = $state(false);

	let implementationGroupsChoices = $state<{ label: string; value: string }[]>([]);

	let defaultImplementationGroups: string[] = $state([]);

	let is_dynamic = $state(false);

	let isLocked = $derived(form.data?.is_locked || object?.is_locked || false);

	let frameworkDefaults = $state<Record<string, any> | null>(null);

	let frameworkScoring = $state<Record<string, any> | null>(null);

	const SCALE_FIELDS = ['score_scale_preset', 'min_score', 'max_score', 'scores_definition'];
	let scaleDirty = $state(false);

	function initialScale(): ScoreScaleValue | null {
		if (!object?.id) return null;
		const current: ScoreScaleValue = {
			score_scale_preset: object.score_scale_preset ?? null,
			min_score: object.min_score,
			max_score: object.max_score,
			scores_definition: scaleLevels(object.scores_definition)
		};
		const fallback = frameworkScoring?.audit_default_scale;
		const sameAsDefault =
			fallback &&
			current.min_score === fallback.min_score &&
			current.max_score === fallback.max_score &&
			current.score_scale_preset === fallback.score_scale_preset &&
			JSON.stringify(current.scores_definition) ===
				JSON.stringify(scaleLevels(fallback.scores_definition));
		return sameAsDefault ? null : current;
	}

	const formErrors = form.errors;
	let rescalePanel = $state<HTMLElement | null>(null);
	let rescaleConfirmButton = $state<HTMLButtonElement | null>(null);
	let rescaleImpact = $derived.by(() => {
		const raw = ($formErrors as Record<string, string[] | undefined>)?.confirm_rescale?.[0];
		if (!raw) return null;
		try {
			return JSON.parse(raw);
		} catch {
			return null;
		}
	});

	$effect(() => {
		if (!rescaleImpact || !rescalePanel) return;
		rescalePanel.scrollIntoView({ block: 'center' });
		rescaleConfirmButton?.focus();
	});

	// The confirmation is single-use: whatever the outcome of the submission it
	// was sent with, the next one has to be confirmed again.
	const submitting = form.submitting;
	let wasSubmitting = false;
	$effect(() => {
		const busy = $submitting;
		untrack(() => {
			if (wasSubmitting && !busy && $formData.confirm_rescale) {
				form.form.update((d) => ({ ...d, confirm_rescale: false }), { taint: false });
			}
			wasSubmitting = busy;
		});
	});

	const SCALE_ERROR_FIELDS = [...SCALE_FIELDS, 'target_score'];
	let scaleErrors = $derived(
		SCALE_ERROR_FIELDS.flatMap(
			(f) => ($formErrors as Record<string, string[] | undefined>)?.[f] ?? []
		)
	);

	function confirmRescale() {
		form.form.update((d) => ({ ...d, confirm_rescale: true }), { taint: false });
		form.submit();
	}

	function dismissRescale() {
		const saveButton = rescalePanel
			?.closest('form')
			?.querySelector<HTMLButtonElement>('[data-testid="save-button"]');
		form.errors.update((e) => ({ ...e, confirm_rescale: undefined }));
		saveButton?.focus();
	}

	function onScaleChange(value: ScoreScaleValue | null) {
		scaleDirty = true;
		form.form.update((d) => ({
			...d,
			confirm_rescale: false,
			score_scale_preset: value?.score_scale_preset ?? null,
			min_score: value?.min_score ?? null,
			max_score: value?.max_score ?? null,
			scores_definition: value?.scores_definition ?? null
		}));
	}

	$effect(() => {
		if (!object?.id || scaleDirty) return;
		untrack(() => {
			if (SCALE_FIELDS.every((f) => $formData[f] === undefined)) return;
			form.form.update(
				(d) => {
					const next = { ...d };
					for (const f of SCALE_FIELDS) delete next[f];
					return next;
				},
				{ taint: false }
			);
		});
	});

	let scoringEnabled = $derived(
		($formData.field_visibility?.score ?? frameworkDefaults?.score)?.auditor !== 'hidden'
	);

	let frameworkRequest = 0;

	// A copy of an audit on the same framework keeps the baseline's scale by
	// default (the backend applies the same rule), so show that as "Default".
	async function applyBaselineDefault(frameworkId: string, request: number) {
		if (!initialData.baseline) return;
		const baseline = await fetch(`/compliance-assessments/${initialData.baseline}`)
			.then((r) => (r.ok ? r.json() : null))
			.catch(() => null);
		if (request !== frameworkRequest || baseline?.framework?.id !== frameworkId) return;
		frameworkScoring = {
			...frameworkScoring,
			audit_default_scale: {
				source: 'baseline',
				score_scale_preset: baseline.score_scale_preset ?? null,
				min_score: baseline.min_score,
				max_score: baseline.max_score,
				scores_definition: baseline.scores_definition ?? null
			}
		};
	}

	async function handleFrameworkChange(id: string) {
		const request = ++frameworkRequest;
		if (!id) frameworkScoring = null;
		if (id) {
			await fetch(`/frameworks/${id}`)
				.then((r) => r.json())
				.then((r) => {
					if (request !== frameworkRequest) return;
					is_dynamic = r['is_dynamic'] || false;
					const implementation_groups = r['implementation_groups_definition'] || [];
					implementationGroupsChoices = implementation_groups.map((group) => ({
						label: group.name,
						value: group.ref_id
					}));
					suggestions = r['reference_controls'].length > 0;

					frameworkDefaults = r['effective_field_visibility'] ?? null;

					frameworkScoring = {
						min_score: r['min_score'],
						max_score: r['max_score'],
						scores_definition: r['scores_definition'],
						is_scale_bound: r['is_scale_bound'],
						audit_default_scale: r['audit_default_scale']
					};
					if (!object.id) {
						onScaleChange(null);
						applyBaselineDefault(id, request);
					}

					defaultImplementationGroups = implementation_groups
						.filter((group) => group.default_selected)
						.map((group) => group.ref_id);

					if (!object.id) {
						form.form.update((currentData) => ({
							...currentData,
							selected_implementation_groups: defaultImplementationGroups
						}));
					}
				});
		}
	}
</script>

{#if (context === 'fromBaseline' || context === 'clone') && initialData.baseline}
	<AutocompleteSelect
		{form}
		field="baseline"
		cacheLock={cacheLocks['baseline']}
		bind:cachedValue={formDataCache['baseline']}
		label={m.baseline()}
		optionsEndpoint="compliance-assessments"
		hidden
	/>
{/if}
{#if initialData.ebios_rm_studies}
	<AutocompleteSelect
		{form}
		field="ebios_rm_studies"
		multiple
		cacheLock={cacheLocks['ebios_rm_studies']}
		bind:cachedValue={formDataCache['ebios_rm_studies']}
		label={m.ebiosRmStudies()}
		hidden
	/>
{/if}
{#if context === 'fromBaseline' && initialData.baseline}
	<AutocompleteSelect
		{form}
		disabled={object.id}
		optionsEndpoint="compliance-assessments/{page.params.id}/frameworks"
		field="framework"
		cacheLock={cacheLocks['framework']}
		optionsLabelField="str"
		optionsValueField="id"
		bind:cachedValue={formDataCache['framework']}
		label={m.targetFramework()}
		onChange={async (e) => handleFrameworkChange(e)}
		mount={async (e) => handleFrameworkChange(e)}
		additionalMultiselectOptions={{
			liOptionClass: 'flex items-center w-full border-t-8 border-b-8 border-transparent'
		}}
		includeAllOptionFields
	>
		{#snippet optionSnippet(option: Record)}
			<FrameworkResultSnippet {option} />
		{/snippet}
	</AutocompleteSelect>
{:else}
	<AutocompleteSelect
		{form}
		disabled={object.id || context === 'clone'}
		optionsEndpoint="frameworks"
		optionsDetailedUrlParameters={context === 'fromBaseline'
			? [['baseline', initialData.baseline]]
			: []}
		field="framework"
		cacheLock={cacheLocks['framework']}
		bind:cachedValue={formDataCache['framework']}
		label={context === 'clone' ? m.framework() : m.targetFramework()}
		onChange={async (e) => handleFrameworkChange(e)}
		mount={async (e) => handleFrameworkChange(e)}
	/>
{/if}
{#if implementationGroupsChoices.length > 0}
	<AutocompleteSelect
		multiple
		translateOptions={false}
		{form}
		options={implementationGroupsChoices}
		field="selected_implementation_groups"
		cacheLock={cacheLocks['selected_implementation_groups']}
		bind:cachedValue={formDataCache['selected_implementation_groups']}
		label={m.selectedImplementationGroups()}
		helpText={is_dynamic ? m.selectedImplementationGroupsDynamicHelpText() : undefined}
	/>
{/if}
<TextField
	{form}
	field="version"
	label={m.version()}
	helpText={m.versionHelpText()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<TextField
	type="date"
	{form}
	field="eta"
	label={m.eta()}
	helpText={m.etaHelpText()}
	cacheLock={cacheLocks['eta']}
	bind:cachedValue={formDataCache['eta']}
/>
{#if scaleErrors.length && !rescaleImpact}
	<div
		class="flex gap-2 rounded-md border border-error-500 bg-error-50-950 px-3 py-2 text-sm"
		role="alert"
		data-testid="score-scale-errors"
	>
		<i class="fa-solid fa-circle-exclamation mt-0.5"></i>
		<ul>
			{#each scaleErrors as error}
				<li>{error}</li>
			{/each}
		</ul>
	</div>
{/if}
{#if rescaleImpact}
	<div
		bind:this={rescalePanel}
		class="space-y-2 rounded-md border border-warning-500 bg-warning-50-950 px-3 py-2 text-sm"
		role="alertdialog"
		aria-labelledby="score-rescale-title"
		data-testid="score-rescale-confirmation"
	>
		<p id="score-rescale-title" class="flex gap-2 font-medium">
			<i class="fa-solid fa-triangle-exclamation mt-0.5"></i>
			{m.scoreScaleConfirmTitle({
				from: rescaleImpact.from.join('–'),
				to: rescaleImpact.to.join('–')
			})}
		</p>
		<ul class="list-disc pl-8 text-xs">
			{#if rescaleImpact.scored}
				<li>{m.scoreScaleConfirmScored({ count: rescaleImpact.scored })}</li>
			{/if}
			{#if rescaleImpact.scores}
				<li>{m.scoreScaleConfirmScores({ count: rescaleImpact.scores })}</li>
			{/if}
			{#if rescaleImpact.documentation_scores}
				<li>
					{m.scoreScaleConfirmDocScores({ count: rescaleImpact.documentation_scores })}
				</li>
			{/if}
			{#if rescaleImpact.target}
				<li>
					{m.scoreScaleConfirmTarget({
						from: rescaleImpact.target[0],
						to: rescaleImpact.target[1]
					})}
				</li>
			{/if}
		</ul>
		<p class="text-xs text-surface-600-400">{m.scoreScaleConfirmIrreversible()}</p>
		{#if rescaleImpact.scored}
			<p class="text-xs text-surface-600-400">{m.scoreScaleConfirmHistory()}</p>
		{/if}
		<div class="flex gap-2">
			<button
				type="button"
				class="btn btn-sm preset-filled-warning-500"
				onclick={confirmRescale}
				bind:this={rescaleConfirmButton}
				data-testid="score-rescale-confirm">{m.scoreScaleConfirmSave()}</button
			>
			<button type="button" class="btn btn-sm preset-tonal-surface" onclick={dismissRescale}
				>{m.cancel()}</button
			>
		</div>
	</div>
{/if}
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<div class="space-y-4">
		{#if context === 'create' && suggestions}
			<Checkbox
				{form}
				field="create_applied_controls_from_suggestions"
				label={m.suggestControls()}
				helpText={m.createAppliedControlsFromSuggestionsHelpText()}
				cacheLock={cacheLocks['create_applied_controls_from_suggestions']}
				bind:cachedValue={formDataCache['create_applied_controls_from_suggestions']}
			/>
		{/if}
		<!-- Visibility editor renders for both create and edit. On create, pills
		     fall back to the framework's `effective_field_visibility` (served by
		     the backend), so what the user sees always matches what the backend
		     will save when no explicit override is provided. -->
		<VisibilityEditor
			value={$formData.field_visibility}
			onChange={(next) => form.form.update((d) => ({ ...d, field_visibility: next }))}
			disabled={object?.is_locked}
			{frameworkDefaults}
		/>

		{#if frameworkScoring}
			{#key frameworkScoring}
				<ScoreScaleEditor
					value={initialScale()}
					onChange={onScaleChange}
					defaultScale={frameworkScoring.audit_default_scale}
					declaredRange={frameworkScoring.min_score !== 0 ||
					frameworkScoring.max_score !== 100 ||
					scaleLevels(frameworkScoring.scores_definition).length
						? { min: frameworkScoring.min_score, max: frameworkScoring.max_score }
						: null}
					isScaleBound={frameworkScoring.is_scale_bound}
					currentRange={object?.id ? { min: object.min_score, max: object.max_score } : null}
					{scoringEnabled}
				/>
			{/key}
		{/if}

		{#if scoringEnabled}
			<Select
				{form}
				options={model.selectOptions['score_calculation_method']}
				field="score_calculation_method"
				label={m.scoreCalculationMethod()}
				helpText={m.scoreCalculationMethodHelpText()}
				cacheLock={cacheLocks['score_calculation_method']}
				bind:cachedValue={formDataCache['score_calculation_method']}
				disableDoubleDash
			/>
			<TextField
				{form}
				type="number"
				step="any"
				field="target_score"
				label={m.targetScore()}
				helpText={m.targetScoreHelpText()}
				cacheLock={cacheLocks['target_score']}
				bind:cachedValue={formDataCache['target_score']}
			/>
			<Checkbox
				{form}
				field="anchor_na_to_target"
				label={m.anchorNaToTarget()}
				helpText={m.anchorNaToTargetHelpText()}
				cacheLock={cacheLocks['anchor_na_to_target']}
				bind:cachedValue={formDataCache['anchor_na_to_target']}
			/>
		{/if}
	</div>
	<AutocompleteSelect
		multiple
		lazy
		{form}
		optionsEndpoint="assets"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
		optionsInfoFields={{
			fields: [
				{
					field: 'type'
				}
			],
			classes: 'text-blue-500'
		}}
		field="assets"
		label={m.assets()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="evidences"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
		field="evidences"
		label={m.evidences()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="actors"
		optionsLabelField="str"
		optionsInfoFields={{
			fields: [{ field: 'type', translate: true }],
			position: 'prefix'
		}}
		field="authors"
		cacheLock={cacheLocks['authors']}
		bind:cachedValue={formDataCache['authors']}
		label={m.authors()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="actors"
		optionsLabelField="str"
		optionsInfoFields={{
			fields: [{ field: 'type', translate: true }],
			position: 'prefix'
		}}
		field="reviewers"
		cacheLock={cacheLocks['reviewers']}
		bind:cachedValue={formDataCache['reviewers']}
		label={m.reviewers()}
	/>
	<TextField
		type="date"
		{form}
		field="due_date"
		label={m.dueDate()}
		helpText={m.dueDateHelpText()}
		cacheLock={cacheLocks['due_date']}
		bind:cachedValue={formDataCache['due_date']}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	{#if !page.data.user.is_third_party}
		<Checkbox
			{form}
			field="is_locked"
			label={m.isLocked()}
			helpText={m.isLockedHelpText()}
			cacheLock={cacheLocks['is_locked']}
			bind:cachedValue={formDataCache['is_locked']}
		/>
		<Checkbox
			{form}
			field="auto_sync"
			label={m.autoSync()}
			helpText={m.autoSyncHelpText()}
			cacheLock={cacheLocks['auto_sync']}
			bind:cachedValue={formDataCache['auto_sync']}
		/>
	{/if}
</Dropdown>
