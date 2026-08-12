<script lang="ts">
	import { untrack } from 'svelte';
	import { formFieldProxy, type SuperValidated } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		form: SuperValidated<any>;
		object?: any;
		chartType?: string;
		isBreakdownMetric?: boolean;
	}

	let { form, object = {}, chartType = '', isBreakdownMetric = false }: Props = $props();

	const { value: widgetConfigValue } = formFieldProxy(form, 'widget_config');

	type Threshold = { op: string; value: number | ''; color: string };

	const initialThresholds: Threshold[] = Array.isArray(object?.widget_config?.thresholds)
		? object.widget_config.thresholds.map((t: any) => ({
				op: typeof t?.op === 'string' ? t.op : '<',
				value: typeof t?.value === 'number' ? t.value : '',
				color: typeof t?.color === 'string' ? t.color : '#3b82f6'
			}))
		: [];
	let thresholds = $state<Threshold[]>(initialThresholds);

	const SCALAR_CHART_TYPES = ['kpi_card', 'gauge', 'sparkline'];
	const visible = $derived(!isBreakdownMetric && SCALAR_CHART_TYPES.includes(chartType));

	const OP_OPTIONS = [
		{ value: '<', label: '<' },
		{ value: '<=', label: '≤' },
		{ value: '>', label: '>' },
		{ value: '>=', label: '≥' },
		{ value: '==', label: '=' },
		{ value: '!=', label: '≠' }
	];

	function addThreshold() {
		thresholds = [...thresholds, { op: '<', value: '', color: '#dc2626' }];
	}
	function removeThreshold(idx: number) {
		thresholds = thresholds.filter((_, i) => i !== idx);
	}
	function applyTrafficLightPreset() {
		thresholds = [
			{ op: '<', value: 50, color: '#dc2626' },
			{ op: '<', value: 80, color: '#eab308' },
			{ op: '>=', value: 80, color: '#22c55e' }
		];
	}

	// Only `thresholds` should drive this effect. Reading $widgetConfigValue here would
	// create a write→read→write loop (a new object reference each pass), so we wrap the
	// merge in untrack().
	$effect(() => {
		const cleaned = thresholds
			.filter((t) => typeof t.value === 'number' && Number.isFinite(t.value))
			.map((t) => ({ op: t.op, value: t.value as number, color: t.color }));
		untrack(() => {
			const base =
				$widgetConfigValue && typeof $widgetConfigValue === 'object'
					? ($widgetConfigValue as Record<string, any>)
					: {};
			const next: Record<string, any> = { ...base };
			if (cleaned.length > 0) {
				next.thresholds = cleaned;
			} else {
				delete next.thresholds;
			}
			$widgetConfigValue = next;
		});
	});
</script>

{#if visible}
	<div class="border-t pt-4 mt-4">
		<div class="flex items-center justify-between mb-2">
			<div>
				<label class="text-sm font-semibold">{safeTranslate('thresholds')}</label>
				<p class="text-xs text-surface-500 mt-0.5">{safeTranslate('thresholdsHint')}</p>
			</div>
			<div class="flex gap-2">
				<button
					type="button"
					class="text-xs text-primary-600 hover:underline"
					onclick={applyTrafficLightPreset}
				>
					{safeTranslate('applyTrafficLightPreset')}
				</button>
				<button
					type="button"
					class="text-xs px-2 py-1 rounded bg-primary-500 text-white hover:bg-primary-600"
					onclick={addThreshold}
				>
					+ {safeTranslate('addThreshold')}
				</button>
			</div>
		</div>
		{#if thresholds.length === 0}
			<p class="text-xs text-surface-400 italic">
				{safeTranslate('noThresholdsConfigured')}
			</p>
		{:else}
			<div class="space-y-2">
				{#each thresholds as t, idx (idx)}
					<div class="flex items-center gap-2">
						<span class="text-xs text-surface-500 w-14">{safeTranslate('ifValue')}</span>
						<select class="select select-sm w-20" bind:value={t.op}>
							{#each OP_OPTIONS as op}
								<option value={op.value}>{op.label}</option>
							{/each}
						</select>
						<input
							type="number"
							step="any"
							class="input input-sm w-28"
							placeholder={safeTranslate('value')}
							bind:value={t.value}
						/>
						<span class="text-xs text-surface-500">{safeTranslate('useColor')}</span>
						<input
							type="color"
							class="w-9 h-8 border rounded cursor-pointer"
							bind:value={t.color}
						/>
						<button
							type="button"
							class="text-xs text-red-600 hover:underline ml-auto"
							onclick={() => removeThreshold(idx)}
						>
							{safeTranslate('remove')}
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
