<script lang="ts">
	// A value typed on the metric's page: no modal. Enter saves. A metric
	// with a frequency records the value for a period, defaulting to the
	// current one; a second value for the period replaces the first.
	import { m } from '#paraglide/messages.js';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { formatMetricNumber, hasPeriods, periodLabel, periodStart } from '#lib/utils/metrics.js';
	import { safeTranslate } from '#lib/utils/i18n.js';

	interface Props {
		metricInstance: any;
		/** The metric's values, newest first: what the chosen period already holds. */
		samples?: any[];
		onSaved?: () => void | Promise<void>;
	}
	let { metricInstance, samples = [], onSaved }: Props = $props();

	const toastStore = getToastStore();
	const definition = $derived(metricInstance?.metric_definition);
	const isQualitative = $derived(definition?.category === 'qualitative');
	const frequency = $derived(metricInstance?.collection_frequency_value);
	const byPeriod = $derived(hasPeriods(frequency));
	const unitName = $derived(definition?.unit?.name ?? '');
	const unitSymbol = $derived(
		unitName === 'percentage' ? '%' : ['score', 'count'].includes(unitName) ? '' : unitName
	);
	const levels = $derived<Array<{ name: string }>>(
		Array.isArray(definition?.choices_definition) ? definition.choices_definition : []
	);

	let value = $state('');
	let choice = $state('');
	let observation = $state('');
	// Any day inside the period names it; the label shows which.
	let periodDay = $state(new Date().toISOString().slice(0, 10));
	let saving = $state(false);
	let error = $state('');
	// An empty or unparsable date names no period: nothing is derived, and
	// the save asks for one.
	const period = $derived.by(() => {
		if (!byPeriod || !periodDay) return null;
		const noon = new Date(`${periodDay}T12:00:00Z`);
		return Number.isNaN(noon.getTime()) ? null : periodStart(noon, frequency);
	});
	const label = $derived(period ? periodLabel(period, frequency) : '');

	// What the chosen period holds today, so replacing it is a conscious act
	// and a missing period is visibly missing.
	const existing = $derived.by(() => {
		if (!period) return null;
		const key = period.toISOString();
		return (
			samples.find((s) => s?.period_start && new Date(s.period_start).toISOString() === key) ?? null
		);
	});
	const existingShown = $derived.by(() => {
		if (!existing) return '';
		const value = typeof existing.value === 'string' ? JSON.parse(existing.value) : existing.value;
		if (isQualitative) {
			const index = Number(value?.choice_index);
			return levels[index - 1]?.name ?? String(value?.choice_index ?? '');
		}
		const shown = formatMetricNumber(value?.result, definition);
		return unitSymbol ? `${shown} ${unitSymbol}` : shown;
	});
	const existingDate = $derived(existing ? new Date(existing.timestamp).toLocaleDateString() : '');

	async function save() {
		// One request at a time: a second Enter must not race the first.
		if (saving) return;
		error = '';
		if (byPeriod && !period) {
			error = m.forPeriod();
			return;
		}
		const body: Record<string, unknown> = {
			metric_instance: metricInstance.id,
			timestamp: new Date().toISOString(),
			observation: observation || null
		};
		if (isQualitative) {
			const index = parseInt(choice);
			if (Number.isNaN(index)) return;
			body.value = { choice_index: index };
		} else {
			const n = parseFloat(value);
			if (Number.isNaN(n)) return;
			body.value = { result: n };
		}
		if (period) body.period_start = period.toISOString();
		saving = true;
		try {
			const res = await fetch('/fe-api/metrology/record-value', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				const first = Object.values(data)[0];
				error = Array.isArray(first) ? safeTranslate(String(first[0])) : m.valueNotSaved();
				return;
			}
			toastStore.trigger({ message: m.valueSaved(), background: 'preset-filled-success-500' });
			value = '';
			choice = '';
			observation = '';
		} catch {
			error = m.valueNotSaved();
			return;
		} finally {
			saving = false;
		}
		// Saved: a refresh that fails is the page's problem, not the value's.
		try {
			await onSaved?.();
		} catch {
			/* the page reloads on its own next navigation */
		}
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			save();
		}
	}
</script>

<div
	class="card p-4 bg-primary-50 dark:bg-primary-950 border border-primary-200 dark:border-primary-800 shadow-sm flex flex-wrap items-end gap-3"
	data-testid="record-value-strip"
>
	<div class="flex flex-col gap-1 w-44">
		<label class="text-sm font-semibold" for="record-value">{m.recordAValue()}</label>
		{#if isQualitative}
			<select id="record-value" class="select" bind:value={choice} onkeydown={onKeydown}>
				<option value="">-- {m.select()} --</option>
				{#each levels as level, index (index)}
					<option value={String(index + 1)}>{index + 1}. {level.name}</option>
				{/each}
			</select>
		{:else}
			<div class="relative">
				<input
					id="record-value"
					type="number"
					step="any"
					class="input pr-10 font-semibold"
					bind:value
					onkeydown={onKeydown}
					data-testid="record-value-input"
				/>
				{#if unitSymbol}
					<span class="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-surface-500"
						>{unitSymbol}</span
					>
				{/if}
			</div>
		{/if}
	</div>
	{#if byPeriod}
		<div class="flex flex-col gap-1 w-48">
			<label class="text-sm font-semibold" for="record-period">{m.forPeriod()} · {label}</label>
			<input
				id="record-period"
				type="date"
				class="input"
				bind:value={periodDay}
				max={new Date().toISOString().slice(0, 10)}
			/>
		</div>
	{/if}
	<div class="flex flex-col gap-1 flex-1 min-w-48">
		<label class="text-sm font-semibold" for="record-observation">{m.observation()}</label>
		<input id="record-observation" class="input" bind:value={observation} onkeydown={onKeydown} />
	</div>
	<button
		type="button"
		class="btn preset-filled-primary-500"
		onclick={save}
		disabled={saving}
		data-testid="record-value-save"
	>
		<i class="fa-solid {saving ? 'fa-spinner fa-spin' : 'fa-check'} mr-2" aria-hidden="true"
		></i>{m.save()}
	</button>
	{#if byPeriod && period}
		<p class="w-full text-xs text-surface-500 m-0" data-testid="record-value-existing">
			{#if existing}
				{m.periodHasValue({ period: label, value: existingShown, date: existingDate })}
			{:else}
				{m.periodHasNoValue({ period: label })}
			{/if}
		</p>
	{/if}
	{#if error}
		<p class="w-full text-xs text-error-500 m-0" role="alert">{error}</p>
	{/if}
</div>
