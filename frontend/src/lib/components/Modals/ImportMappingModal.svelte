<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	const modalStore: ModalStore = getModalStore();

	interface Analysis {
		delimiter: string;
		headers: string[];
		row_count: number;
		columns: Record<string, { distinct: number | string; values: string[] | null }>;
	}

	interface Props {
		parent: any;
		analysis: Analysis | null;
		fileName: string;
		assets: { id: string; name: string }[];
	}

	let { parent, analysis, fileName, assets }: Props = $props();

	const RESULT_TARGETS = ['pass', 'fail', 'not_applicable', 'error', 'not_checked'];
	const targetLabels: Record<string, string> = {
		pass: m.pass(),
		fail: m.fail(),
		not_applicable: m.notApplicable(),
		error: m.error(),
		not_checked: m.notChecked(),
		ignore: m.ignore()
	};
	const AGGREGATIONS = [
		{ value: 'worst_case', label: m.aggregationWorstCase() },
		{ value: 'best_case', label: m.aggregationBestCase() },
		{ value: 'last_row', label: m.aggregationLastRow() },
		{ value: 'strict', label: m.aggregationStrict() }
	];

	interface Preset {
		key: string;
		label: string;
		columns: Record<string, string>;
		values: Record<string, string>;
		aggregation: string;
	}
	const PRESETS: Preset[] = [
		{
			key: 'standard',
			label: m.importPresetStandard(),
			columns: {
				ref_id: 'ref_id',
				result: 'result',
				message: 'message',
				actual: 'actual',
				expected: 'expected'
			},
			values: Object.fromEntries(RESULT_TARGETS.map((v) => [v, v])),
			aggregation: 'strict'
		},
		{
			key: 'prowler',
			label: m.importPresetProwler(),
			columns: {
				ref_id: 'REQUIREMENTS_ID',
				result: 'STATUS',
				message: 'STATUSEXTENDED'
			},
			values: { PASS: 'pass', FAIL: 'fail', MANUAL: 'not_checked' },
			aggregation: 'worst_case'
		}
	];

	const OPTIONAL_COLUMNS = ['message', 'actual', 'expected'] as const;
	const columnLabels: Record<string, string> = {
		ref_id: m.refId(),
		result: m.result(),
		message: m.importColumnMessage(),
		actual: m.actual(),
		expected: m.expected()
	};

	let cols = $state<Record<string, string>>({
		ref_id: '',
		result: '',
		message: '',
		actual: '',
		expected: ''
	});
	let assetMode = $state<'pick' | 'column'>('pick');
	let assetCol = $state('');
	let aggregation = $state('worst_case');
	let valueMap = $state<Record<string, string>>({});
	let appliedPreset = $state('');
	let assetFilter = $state('');
	let selectedAssets = $state<string[]>(assets.length === 1 ? [assets[0].id] : []);

	const filteredAssets = $derived(
		assetFilter
			? assets.filter((a) => a.name.toLowerCase().includes(assetFilter.toLowerCase()))
			: assets
	);

	function toggleAsset(id: string) {
		selectedAssets = selectedAssets.includes(id)
			? selectedAssets.filter((a) => a !== id)
			: [...selectedAssets, id];
	}

	const resultInfo = $derived(analysis && cols.result ? analysis.columns[cols.result] : null);
	const resultValues = $derived(resultInfo?.values ?? []);
	const resultTooManyValues = $derived(Boolean(cols.result && resultInfo?.values == null));

	function seedValueMap(preset?: Preset) {
		const seeded: Record<string, string> = {};
		for (const value of resultValues) {
			if (preset?.values[value]) seeded[value] = preset.values[value];
			else if (RESULT_TARGETS.includes(value.toLowerCase())) seeded[value] = value.toLowerCase();
			else seeded[value] = '';
		}
		valueMap = seeded;
	}

	function applyPreset(preset: Preset) {
		if (!analysis) return;
		appliedPreset = preset.key;
		for (const key of Object.keys(cols)) {
			const wanted = preset.columns[key];
			cols[key] = wanted && analysis.headers.includes(wanted) ? wanted : '';
		}
		aggregation = preset.aggregation;
		seedValueMap(preset);
	}

	function onResultColumnChange() {
		appliedPreset = '';
		seedValueMap();
	}

	const presetMatches = (preset: Preset) =>
		Object.values(preset.columns).filter((c) => analysis?.headers.includes(c)).length;

	const mappingValid = $derived(
		!analysis ||
			(Boolean(cols.ref_id) &&
				Boolean(cols.result) &&
				!resultTooManyValues &&
				resultValues.length > 0 &&
				resultValues.every((value) => valueMap[value]))
	);
	const targetsValid = $derived(
		assetMode === 'column' ? Boolean(assetCol) : selectedAssets.length > 0
	);
	const canConfirm = $derived(mappingValid && targetsValid);

	function confirm() {
		let mapping: object | null = null;
		if (analysis) {
			const columns: Record<string, string> = { ref_id: cols.ref_id, result: cols.result };
			for (const key of OPTIONAL_COLUMNS) if (cols[key]) columns[key] = cols[key];
			if (assetMode === 'column') columns.asset = assetCol;
			mapping = {
				delimiter: analysis.delimiter,
				columns,
				values: valueMap,
				aggregation
			};
		}
		const payload = {
			mapping,
			assetIds: assetMode === 'pick' ? selectedAssets : []
		};
		if ($modalStore[0]?.response) $modalStore[0].response(payload);
		modalStore.close();
	}
</script>

{#if $modalStore[0]}
	<div
		class="card bg-surface-50-950 p-4 w-modal-wide max-w-4xl shadow-xl space-y-4 overflow-y-auto max-h-[90vh]"
		data-testid="import-mapping-modal"
	>
		<header class="text-2xl font-bold">{m.importResults()}</header>
		<p class="text-sm text-surface-600-400">
			{fileName}{#if analysis}
				— {m.importMappingSubtitle({ rows: analysis.row_count })}{/if}
		</p>

		{#if analysis}
			<div class="flex items-center gap-2 flex-wrap">
				<span class="text-sm font-semibold">{m.importPresets()}:</span>
				{#each PRESETS as preset}
					<button
						type="button"
						class="btn btn-sm {appliedPreset === preset.key
							? 'preset-filled-primary-500'
							: 'preset-outlined-surface-500'}"
						disabled={presetMatches(preset) === 0}
						onclick={() => applyPreset(preset)}
						data-testid="import-preset-{preset.key}"
					>
						{preset.label}
					</button>
				{/each}
			</div>

			<div class="grid grid-cols-2 md:grid-cols-3 gap-3">
				{#each Object.keys(cols) as key}
					<label class="label text-sm">
						<span>
							{columnLabels[key]}
							{#if key === 'ref_id' || key === 'result'}<span class="text-error-500">*</span>{/if}
						</span>
						<select
							class="select"
							bind:value={cols[key]}
							onchange={() => key === 'result' && onResultColumnChange()}
							data-testid="import-col-{key}"
						>
							<option value="">—</option>
							{#each analysis.headers as header}
								<option value={header}>{header}</option>
							{/each}
						</select>
					</label>
				{/each}
			</div>
		{/if}

		<div class="space-y-2">
			<span class="text-sm font-semibold">{m.importSelectAssets()}</span>
			{#if analysis}
				<div class="flex items-center gap-4 text-sm">
					<label class="flex items-center gap-2">
						<input type="radio" class="radio" bind:group={assetMode} value="pick" />
						{m.importPickAssets()}
					</label>
					<label class="flex items-center gap-2">
						<input type="radio" class="radio" bind:group={assetMode} value="column" />
						{m.importAssetFromColumn()}
					</label>
					{#if assetMode === 'column'}
						<select class="select w-auto" bind:value={assetCol} data-testid="import-col-asset">
							<option value="">—</option>
							{#each analysis.headers as header}
								<option value={header}>{header}</option>
							{/each}
						</select>
					{/if}
				</div>
				<p class="text-xs text-surface-500">
					{assetMode === 'column' ? m.importAssetFromColumnHelp() : m.importPickAssetsHelp()}
				</p>
			{/if}
			{#if assetMode === 'pick'}
				<div class="border border-surface-200-800 rounded-sm p-2 space-y-1">
					{#if assets.length > 8}
						<input
							type="text"
							class="input text-sm"
							placeholder={m.search()}
							bind:value={assetFilter}
							data-testid="import-asset-filter"
						/>
					{/if}
					<div class="max-h-40 overflow-y-auto space-y-1" data-testid="import-asset-picker">
						{#each filteredAssets as asset (asset.id)}
							<label class="flex items-center gap-2 text-sm">
								<input
									type="checkbox"
									class="checkbox"
									checked={selectedAssets.includes(asset.id)}
									onchange={() => toggleAsset(asset.id)}
								/>
								{asset.name}
							</label>
						{:else}
							<p class="text-xs text-surface-500">{m.noEntriesFound()}</p>
						{/each}
					</div>
					{#if selectedAssets.length > 1}
						<p class="text-xs text-surface-500">
							{m.importMultiAssetHint({ count: selectedAssets.length })}
						</p>
					{/if}
				</div>
			{/if}
		</div>

		{#if analysis}
			{#if resultTooManyValues}
				<p class="text-sm text-warning-600-400">{m.importResultColumnTooManyValues()}</p>
			{:else if resultValues.length}
				<div class="space-y-1">
					<span class="text-sm font-semibold">{m.importValueBindings()}</span>
					<div class="grid grid-cols-2 md:grid-cols-3 gap-2">
						{#each resultValues as value}
							<label class="label text-sm">
								<span class="font-mono text-xs">{value || m.importEmptyValue()}</span>
								<select
									class="select"
									bind:value={valueMap[value]}
									data-testid="import-value-{value}"
								>
									<option value="">—</option>
									{#each [...RESULT_TARGETS, 'ignore'] as target}
										<option value={target}>{targetLabels[target]}</option>
									{/each}
								</select>
							</label>
						{/each}
					</div>
				</div>
			{/if}

			<label class="label text-sm max-w-xs">
				<span class="font-semibold">{m.aggregation()}</span>
				<select class="select" bind:value={aggregation} data-testid="import-aggregation">
					{#each AGGREGATIONS as opt}
						<option value={opt.value}>{opt.label}</option>
					{/each}
				</select>
				<span class="text-xs text-surface-500">{m.importAggregationHelp()}</span>
			</label>
		{/if}

		<footer class="flex justify-end gap-2">
			<button type="button" class="btn preset-tonal" onclick={parent.onClose}>{m.cancel()}</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={!canConfirm}
				onclick={confirm}
				data-testid="import-mapping-confirm"
			>
				{m.importButton()}
			</button>
		</footer>
	</div>
{/if}
