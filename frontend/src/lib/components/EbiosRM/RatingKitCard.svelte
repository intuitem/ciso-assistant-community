<script lang="ts">
	import { m } from '$paraglide/messages';
	import { ratingLevelLabel } from '$lib/utils/ebios-rating-kit';
	import type { RatingKit } from '$lib/utils/ebios-quotation';

	interface Props {
		kit: RatingKit & {
			likelihood: { name: string; hexcolor?: string }[];
			matrix: { id: string; name: string };
			customized: boolean;
		};
		advanced: boolean;
	}

	let { kit, advanced }: Props = $props();

	const levels = $derived([...kit.likelihood.keys()].reverse());
</script>

<div class="card p-4 bg-surface-50-950 border border-surface-200-800 shadow-sm space-y-3">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h3 class="font-semibold text-surface-700-300 flex items-center gap-2">
			<i class="fa-solid fa-scale-balanced text-purple-500"></i>
			{m.ebiosRmRatingScales()}
		</h3>
		<p class="text-xs text-surface-600-400">
			{kit.customized ? m.ebiosRmRatingScalesFromMatrix() : m.ebiosRmRatingScalesDefaults()}
			<a href="/risk-matrices/{kit.matrix.id}" class="anchor">{kit.matrix.name}</a>
		</p>
	</div>
	<div class="flex flex-wrap gap-6">
		<table class="text-sm">
			<thead>
				<tr class="text-xs text-surface-600-400">
					<th class="text-left font-medium pr-4">{m.likelihood()}</th>
					<th class="text-left font-medium pr-4">{m.successProbability()}</th>
					{#if advanced}
						<th class="text-left font-medium">{m.technicalDifficulty()}</th>
					{/if}
				</tr>
			</thead>
			<tbody>
				{#each levels as level}
					<tr>
						<td class="pr-4 py-0.5">
							<span
								class="badge text-xs"
								style={kit.likelihood[level].hexcolor
									? `background-color: ${kit.likelihood[level].hexcolor}`
									: ''}>{kit.likelihood[level].name}</span
							>
						</td>
						<td class="pr-4">{ratingLevelLabel(kit.success_probability[level])}</td>
						{#if advanced}
							<td>{ratingLevelLabel(kit.technical_difficulty[level])}</td>
						{/if}
					</tr>
				{/each}
			</tbody>
		</table>
		{#if advanced}
			<div>
				<p class="text-xs text-surface-600-400 mb-1">{m.lbEbiosRmLikelihoodGrid()}</p>
				<table class="text-xs" data-testid="likelihood-grid">
					<tbody>
						{#each levels as probability}
							<tr>
								<th class="pr-2 text-right font-medium text-surface-600-400">
									{ratingLevelLabel(kit.success_probability[probability])}
								</th>
								{#each kit.technical_difficulty as _, difficulty}
									{@const value = kit.likelihood_grid[probability][difficulty]}
									<td
										class="w-8 h-6 text-center border border-surface-50-950"
										style={kit.likelihood[value]?.hexcolor
											? `background-color: ${kit.likelihood[value].hexcolor}`
											: ''}
										title={kit.likelihood[value]?.name}>{value + 1}</td
									>
								{/each}
							</tr>
						{/each}
						<tr>
							<th></th>
							{#each kit.technical_difficulty as level}
								<th
									class="px-0.5 pt-1 font-medium text-surface-600-400 [writing-mode:vertical-rl] rotate-180 text-left"
									>{ratingLevelLabel(level)}</th
								>
							{/each}
						</tr>
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>
