<script lang="ts" module>
	// A computed metric whose formula is its definition's (inputs combining
	// every metric of a kind, or a formula over objects), as the composition
	// endpoint hands it over.
	export interface DefinitionComposition {
		composable: false;
		definition: { id: string; name: string; shared_with: number };
		expression: string;
		folder: { id: string; str: string };
		collection_frequency: string | null;
		last_computed_at: string | null;
		can_change_definition: boolean;
	}
</script>

<script lang="ts">
	// The formula drawer for such a metric: the definition form's formula
	// block, previewed where this metric lives and at its frequency, with the
	// metric as it is now beside the result. A save changes the definition,
	// which every metric using it follows: the drawer says so.
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { getToastStore } from '$lib/components/Toast/stores';
	import DefinitionFormulaEditor, { type FormulaPreview } from './DefinitionFormulaEditor.svelte';
	import FormulaSparkline from './FormulaSparkline.svelte';
	import type { Saved } from './ComposeMetricEditor.svelte';
	import { levelIndex, samplesOnPeriods, type Level } from '$lib/utils/derived-metrics';

	interface Props {
		instanceId: string;
		composition: DefinitionComposition;
		onClose: () => void;
		onSaved: (saved: Saved) => void;
	}

	let { instanceId, composition, onClose, onSaved }: Props = $props();

	const toastStore = getToastStore();
	const chatBubble = $derived(Boolean(page.data?.featureflags?.chat_mode));
	const titleId = $props.id();

	// The formula block binds to a form: this one, never posted, holds the
	// definition's formula while it is edited here.
	const schema = z.object({
		inputs: z.any(),
		datasets: z.any(),
		expression: z.string(),
		folder: z.string()
	});
	const formulaForm = superForm(
		defaults({ inputs: null, datasets: null, expression: '', folder: '' }, zod(schema)),
		{ dataType: 'json', taintedMessage: false, validators: zod(schema), SPA: true }
	);
	const { form: formula } = formulaForm;

	let definition = $state<Record<string, unknown> | null>(null);
	let loadFailed = $state(false);
	let initial = $state<string | null>(null);
	const current = $derived(
		JSON.stringify([$formula.inputs ?? null, $formula.datasets ?? null, $formula.expression ?? ''])
	);
	const edited = $derived(initial !== null && current !== initial);

	const isLevel = $derived(definition?.category === 'qualitative');
	const levels = $derived(
		(Array.isArray(definition?.choices_definition) ? definition.choices_definition : []).map(
			(choice: { ref_id?: unknown; name?: unknown }) => ({
				ref_id: String(choice?.ref_id ?? ''),
				name: String(choice?.name ?? '')
			})
		) as Level[]
	);

	// Previewed where this metric lives and how often it is computed: what
	// it would hold. Another domain or frequency is a try, with no "now".
	let previewFolder = $state(composition.folder.id);
	let previewFrequency = $state(composition.collection_frequency ?? 'monthly');
	let preview = $state<FormulaPreview | null>(null);
	const ownPreview = $derived(
		previewFolder === composition.folder.id &&
			previewFrequency === (composition.collection_frequency ?? 'monthly')
	);

	const CHART = { width: 480, height: 120, periods: 24 };
	const chartPeriods = $derived(
		(preview?.periods ?? [])
			.slice(-CHART.periods)
			.map((period) => (isLevel ? { ...period, value: levelIndex(period.value, levels) } : period))
	);
	let samples = $state<{ timestamp: string; period_start?: string | null; value: unknown }[]>([]);
	const nowPeriods = $derived(
		ownPreview && samples.length && chartPeriods.length
			? samplesOnPeriods(chartPeriods, samples, (value) =>
					isLevel ? Number(value.choice_index) || null : value.result
				)
			: []
	);
	function formatPoint(value: number): string {
		if (isLevel) return levels[value - 1]?.name ?? String(value);
		return Number.isInteger(value) ? String(value) : value.toFixed(2);
	}

	let saving = $state(false);
	let errors = $state<string[]>([]);
	const canSave = $derived(composition.can_change_definition && edited && !saving);

	async function save(event?: Event) {
		event?.preventDefault();
		if (!canSave) return;
		saving = true;
		errors = [];
		try {
			const res = await fetch(`/fe-api/metrology/metric-definitions/${composition.definition.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					inputs: $formula.inputs ?? null,
					datasets: $formula.datasets ?? null,
					expression: $formula.expression ?? ''
				})
			});
			if (res.ok) {
				// The definition's metrics recompute on their schedule: this one,
				// read beside the drawer, now (refused without the right to
				// change it, and then it waits for the schedule too).
				await fetch(`/fe-api/metrology/refresh-metric-instance/${instanceId}`, {
					method: 'POST'
				}).catch(() => {});
				toastStore.trigger({
					message: m.computedMetricSaved(),
					background: 'preset-filled-success-500'
				});
				// The stamp before the recomputation the save queued.
				onSaved({ id: instanceId, last_computed_at: composition.last_computed_at });
				return;
			}
			const body = await res.json().catch(() => ({}));
			errors =
				res.status === 400 && body && typeof body === 'object'
					? Object.values(body)
							.flat()
							.map((message) => String(message))
					: [m.anErrorOccurred()];
		} catch {
			errors = [m.anErrorOccurred()];
		} finally {
			saving = false;
		}
	}

	// Closing on an edit not saved asks first, as the other drawer does.
	let confirmingClose = $state(false);
	function requestClose() {
		if (edited && !confirmingClose) {
			confirmingClose = true;
			return;
		}
		onClose();
	}
	function onWindowKeydown(event: KeyboardEvent) {
		if (event.key !== 'Escape' || event.defaultPrevented) return;
		if (confirmingClose) confirmingClose = false;
		else requestClose();
	}
	function onFormKeydown(event: KeyboardEvent) {
		if (event.key !== 'Enter') return;
		if (event.metaKey || event.ctrlKey) {
			event.preventDefault();
			save();
			return;
		}
		// Enter belongs to the fields' own widgets: never a submit here.
		if ((event.target as HTMLElement | null)?.tagName === 'INPUT') event.preventDefault();
	}

	let rootEl = $state<HTMLFormElement | null>(null);
	onMount(async () => {
		const params = new URLSearchParams({ metric_instance: instanceId, limit: '200' });
		fetch(`/custom-metric-samples?${params}`)
			.then((res) => (res.ok ? res.json() : []))
			.then((body) => {
				samples = Array.isArray(body) ? body : (body?.results ?? []);
			})
			.catch(() => {});
		try {
			const res = await fetch(`/fe-api/metrology/metric-definitions/${composition.definition.id}`);
			if (!res.ok) throw new Error();
			const body = await res.json();
			const folder = body.folder;
			formulaForm.form.set(
				{
					inputs: body.inputs ?? null,
					datasets: body.datasets ?? null,
					expression: body.expression ?? '',
					folder: typeof folder === 'string' ? folder : (folder?.id ?? '')
				},
				{ taint: false }
			);
			definition = body;
			await tick();
			initial = current;
			rootEl?.querySelector<HTMLTextAreaElement>('[data-testid="form-input-expression"]')?.focus();
		} catch {
			loadFailed = true;
		}
	});
</script>

<svelte:window onkeydown={onWindowKeydown} />

<form
	bind:this={rootEl}
	class="flex flex-col h-full min-h-0"
	onsubmit={save}
	onkeydown={onFormKeydown}
	aria-labelledby={titleId}
	data-testid="definition-formula-panel"
>
	<header class="flex items-start justify-between gap-4 p-4 border-b border-surface-200-800">
		<div class="flex flex-col gap-1">
			<h2 id={titleId} class="text-lg font-bold flex items-center gap-2">
				<i class="fa-solid fa-calculator text-primary-500" aria-hidden="true"></i>
				{m.editComputedMetric()}
			</h2>
			<p class="text-sm text-surface-600-400">
				{m.formulaOfDefinition({ name: composition.definition.name })}
			</p>
		</div>
		<button
			type="button"
			aria-label={m.close()}
			class="btn-icon hover:preset-tonal"
			onclick={requestClose}
		>
			<i class="fa-solid fa-xmark"></i>
		</button>
	</header>

	<div class="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-4">
		{#if !composition.can_change_definition}
			<p
				class="rounded-base border border-surface-300-700 bg-surface-100-900 p-3 text-sm"
				data-testid="definition-formula-read-only"
			>
				<i class="fa-solid fa-lock mr-1" aria-hidden="true"></i>{m.definitionNotYours()}
			</p>
		{/if}
		{#if loadFailed}
			<p class="text-sm text-error-500">{m.anErrorOccurred()}</p>
		{:else if definition}
			<DefinitionFormulaEditor
				form={formulaForm}
				{definition}
				category={definition.category}
				choicesDefinition={definition.choices_definition}
				bind:previewFolder
				bind:previewFrequency
				bind:preview
			>
				{#snippet previewTop()}
					<FormulaSparkline
						periods={chartPeriods}
						now={nowPeriods}
						width={CHART.width}
						height={CHART.height}
						format={formatPoint}
						testid="definition-formula-chart"
					/>
				{/snippet}
			</DefinitionFormulaEditor>
		{:else}
			<i class="fa-solid fa-spinner fa-spin text-surface-500" aria-hidden="true"></i>
		{/if}
		{#each errors as message (message)}
			<p class="text-xs text-error-500">{message}</p>
		{/each}
	</div>

	{#if edited}
		<!-- What a save reaches, said next to the button that does it. -->
		<div
			class="mx-4 mb-3 rounded-base border border-warning-500 bg-warning-50-950 p-3 text-sm flex flex-col gap-2"
			data-testid="definition-formula-scope"
		>
			<p>
				<i class="fa-solid fa-clock-rotate-left mr-1" aria-hidden="true"
				></i>{m.formulaChangeRecomputes()}
			</p>
			{#if composition.definition.shared_with > 0}
				<p>{m.definitionSharedAll({ count: composition.definition.shared_with })}</p>
			{/if}
		</div>
	{/if}
	<footer
		class="flex items-center justify-end gap-2 border-t border-surface-200-800 p-3 {chatBubble
			? 'pr-20'
			: ''}"
	>
		{#if confirmingClose}
			<span class="text-sm font-semibold mr-auto" role="status">{m.unsavedChanges()}</span>
			<button type="button" class="btn preset-tonal" onclick={() => (confirmingClose = false)}
				>{m.keepEditing()}</button
			>
			<button
				type="button"
				class="btn preset-filled-error-500"
				onclick={onClose}
				data-testid="definition-formula-discard">{m.discardChanges()}</button
			>
		{:else}
			<button type="button" class="btn preset-tonal" onclick={requestClose}>{m.cancel()}</button>
			<button
				type="submit"
				class="btn preset-filled-primary-500"
				disabled={!canSave}
				aria-keyshortcuts="Control+Enter Meta+Enter"
				data-testid="definition-formula-save"
			>
				{#if saving}
					<i class="fa-solid fa-spinner fa-spin mr-2" aria-hidden="true"></i>
				{:else}
					<i class="fa-solid fa-check mr-2" aria-hidden="true"></i>
				{/if}
				{m.save()}
			</button>
		{/if}
	</footer>
</form>
