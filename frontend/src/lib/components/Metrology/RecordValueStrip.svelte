<script lang="ts">
	// A value typed on the metric's page: no modal. Enter saves. A metric
	// with a frequency records the value for a period, defaulting to the
	// current one; a second value for the period replaces the first.
	import { m } from '#paraglide/messages.js';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { hasPeriods, periodLabel, periodStart } from '#lib/utils/metrics.js';
	import { safeTranslate } from '#lib/utils/i18n.js';

	interface Props {
		metricInstance: any;
		onSaved?: () => void | Promise<void>;
	}
	let { metricInstance, onSaved }: Props = $props();

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
	const period = $derived(
		byPeriod ? periodStart(new Date(`${periodDay}T12:00:00Z`), frequency) : null
	);
	const label = $derived(period ? periodLabel(period, frequency) : '');

	async function save() {
		error = '';
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
			await onSaved?.();
		} catch {
			error = m.valueNotSaved();
		} finally {
			saving = false;
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
	{#if byPeriod}
		<p class="w-full text-xs text-surface-500 m-0">{m.replacesPeriodValue()}</p>
	{/if}
	{#if error}
		<p class="w-full text-xs text-error-500 m-0" role="alert">{error}</p>
	{/if}
</div>
