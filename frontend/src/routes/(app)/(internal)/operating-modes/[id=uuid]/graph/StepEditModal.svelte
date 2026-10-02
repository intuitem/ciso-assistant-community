<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import { superForm, defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';

	interface StepValues {
		assets: string[];
		assetLabels: string[];
		successProbability: number;
		successProbabilityPct: number | null;
		technicalDifficulty: number;
	}

	interface Props {
		label: string;
		assets: string[];
		assetLabels: string[];
		successProbability: number;
		successProbabilityPct: number | null;
		technicalDifficulty: number;
		probabilityChoices: Record<string, string>;
		difficultyChoices?: Record<string, string> | null;
		// Rating factors of the action's catalogue category (fiche méthode 8)
		ratingHelp?: string | null;
		onApply: (values: StepValues) => void;
		onClose: () => void;
	}
	let {
		label,
		assets,
		assetLabels,
		successProbability,
		successProbabilityPct,
		technicalDifficulty,
		probabilityChoices,
		difficultyChoices = null,
		ratingHelp = null,
		onApply,
		onClose
	}: Props = $props();

	const toOptions = (choices: Record<string, string>) =>
		Object.entries(choices)
			.map(([value, name]) => ({ label: name, value: Number(value) }))
			.sort((a, b) => a.value - b.value);
	const probabilityOptions = toOptions(probabilityChoices);
	const difficultyOptions = difficultyChoices ? toOptions(difficultyChoices) : [];

	const schema = z.object({
		assets: z.array(z.string()).optional(),
		success_probability: z.number().optional(),
		success_probability_pct: z.number().min(0).max(100).nullable().optional(),
		technical_difficulty: z.number().optional()
	});
	const _form = superForm(
		defaults(
			{
				assets,
				success_probability: successProbability,
				success_probability_pct: successProbabilityPct,
				technical_difficulty: technicalDifficulty
			},
			zod(schema)
		),
		{
			dataType: 'json',
			taintedMessage: false,
			SPA: true,
			validators: zod(schema)
		}
	);
	const { form, errors } = _form;

	let selectedAssetOptions: { label: string; value: string | number }[] | undefined = $state();
	const initialLabelById = new Map(assets.map((assetId, index) => [assetId, assetLabels[index]]));

	function apply() {
		const pct = $form.success_probability_pct;
		const selectedAssets = $form.assets ?? [];
		const labelById = new Map(
			(selectedAssetOptions ?? []).map((option) => [String(option.value), option.label])
		);
		onApply({
			assets: selectedAssets,
			assetLabels: selectedAssets.map(
				(assetId) => labelById.get(assetId) ?? initialLabelById.get(assetId) ?? assetId
			),
			successProbability: Number($form.success_probability ?? -1),
			successProbabilityPct: pct === undefined || pct === null || Number.isNaN(pct) ? null : pct,
			technicalDifficulty: Number($form.technical_difficulty ?? -1)
		});
	}
</script>

<div
	class="fixed inset-0 z-[60] flex items-start justify-center bg-black/40 p-4 pt-24"
	role="presentation"
	onclick={onClose}
>
	<div
		class="card bg-surface-50-950 w-modal max-w-md space-y-4 p-4 shadow-xl"
		role="presentation"
		onclick={(e) => e.stopPropagation()}
	>
		<div class="flex items-center justify-between">
			<h3 class="text-lg font-bold">{m.edit()} {m.killChain().toLowerCase()} — {label}</h3>
			<button
				type="button"
				aria-label={m.close()}
				class="cursor-pointer hover:text-primary-500"
				onclick={onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>
		<AutocompleteSelect
			form={_form}
			multiple
			optionsEndpoint="assets?type=SP"
			optionsLabelField="auto"
			optionsExtraFields={[['folder', 'str']]}
			field="assets"
			bind:cachedOptions={selectedAssetOptions}
			label={m.supportingAssets()}
			helpText={m.killChainAssetsHelpText()}
		/>
		<Select
			form={_form}
			options={probabilityOptions}
			field="success_probability"
			disableDoubleDash
			label={m.successProbability()}
			helpText={m.successProbabilityHelpText()}
		/>
		<NumberField
			form={_form}
			field="success_probability_pct"
			cachedValue={undefined}
			step="any"
			min="0"
			max="100"
			label={m.successProbabilityPct()}
			helpText={m.successProbabilityPctHelpText()}
		/>
		{#if difficultyChoices}
			<Select
				form={_form}
				options={difficultyOptions}
				field="technical_difficulty"
				disableDoubleDash
				label={m.technicalDifficulty()}
				helpText={m.technicalDifficultyHelpText()}
			/>
		{/if}
		{#if ratingHelp}
			<details class="rounded-base border border-surface-200-800 px-3 py-2 text-xs">
				<summary class="cursor-pointer font-semibold text-surface-700-300">
					<i class="fa-solid fa-book-open mr-1"></i>{m.ratingHelp()}
				</summary>
				<p class="mt-2 whitespace-pre-line text-surface-700-300">{ratingHelp}</p>
			</details>
		{/if}
		<div class="flex justify-end gap-2">
			<button type="button" class="btn preset-tonal" onclick={onClose}>{m.cancel()}</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={!!$errors.success_probability_pct}
				onclick={apply}
			>
				{m.apply()}
			</button>
		</div>
	</div>
</div>
