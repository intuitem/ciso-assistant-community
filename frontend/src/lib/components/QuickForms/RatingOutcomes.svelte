<script lang="ts">
	import { m } from '#paraglide/messages.js';

	// The form's rating outcomes (`kind: rating`), as the server evaluated them: each
	// page answering all the dimensions is a point, one per stage. Two dimensions draw
	// as a map (rows: the first, columns: the second); any other number as a table.
	interface Level {
		ref_id: string;
		label: string;
		color?: string;
		description?: string;
	}
	interface Dimension {
		ref_id: string;
		label: string;
		levels: Level[];
	}
	interface Point {
		page: string;
		stage: string;
		dims: Record<string, { level: string; rank: number; value: number }>;
		level: string | null;
	}
	interface Rating {
		ref_id: string;
		label: string;
		dimensions: Dimension[];
		levels: Level[];
		grid: (string | null)[][] | null;
		points: Point[];
	}
	interface Props {
		ratings: Rating[];
		pages: any[];
	}

	let { ratings, pages }: Props = $props();

	const CURRENT = 'current';
	const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
	// "Risks: illegitimate access to data" reads "Illegitimate access to data".
	const pageName = (urn: string) => {
		const page = pages.find((p) => p.urn === urn);
		return capitalize(
			String(page?.name || page?.ref_id || urn)
				.split(': ')
				.at(-1)!
		);
	};

	function view(rating: Rating) {
		const levels = Object.fromEntries(rating.levels.map((l) => [l.ref_id, l]));
		// Numbered in page order, so the numbers read like the form.
		const order = pages
			.map((p) => p.urn)
			.filter((urn) => rating.points.some((p) => p.page === urn));
		const rows = order.map((urn, i) => {
			const points = rating.points
				.filter((p) => p.page === urn)
				.sort((a, b) => Number(b.stage === CURRENT) - Number(a.stage === CURRENT));
			return { key: i + 1, urn, name: pageName(urn), points };
		});
		return { levels, rows, keyOf: (urn: string) => rows.find((r) => r.urn === urn)?.key };
	}

	// Dark text only on a level's own (light) colour: without one, the theme's text.
	const onColor = (color?: string | null | false) => (color ? 'text-surface-950' : '');

	const dimLabel = (dimension: Dimension, ref: string) =>
		dimension.levels.find((l) => l.ref_id === ref)?.label ?? ref;
</script>

{#each ratings as rating (rating.ref_id)}
	{@const { levels, rows, keyOf } = view(rating)}
	{@const map = rating.dimensions.length === 2 && rating.grid}
	<div class="card bg-surface-50-950 shadow-sm p-4" data-testid="rating-outcome">
		<h3 class="font-semibold"><i class="fa-solid fa-table-cells mr-2"></i>{rating.label}</h3>
		<div class="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start">
			{#if map}
				{@const [rowDim, colDim] = rating.dimensions}
				<div class="flex max-w-full min-w-0 gap-2 overflow-x-auto">
					<div
						class="flex items-center justify-center text-xs font-semibold text-surface-600-400 [writing-mode:vertical-rl] rotate-180"
					>
						{rowDim.label}
					</div>
					<div>
						<div
							class="grid gap-1"
							style="grid-template-columns: auto repeat({colDim.levels
								.length}, minmax(4.5rem, 1fr));"
						>
							{#each rowDim.levels.toReversed() as rowLevel (rowLevel.ref_id)}
								{@const ri = rowDim.levels.indexOf(rowLevel)}
								<div
									class="flex items-center justify-end pr-2 text-right text-xs text-surface-600-400"
									title={rowLevel.description}
								>
									{rowLevel.label}
								</div>
								{#each colDim.levels as colLevel, ci (colLevel.ref_id)}
									{@const cell = levels[rating.grid?.[ri]?.[ci] ?? '']}
									<div
										class="flex h-14 flex-wrap content-center items-center justify-center gap-1 rounded-base"
										style="background-color: {cell?.color || 'transparent'};"
										title={cell?.label}
									>
										{#each rating.points.filter((p) => p.dims[rowDim.ref_id]?.level === rowLevel.ref_id && p.dims[colDim.ref_id]?.level === colLevel.ref_id) as point (point.page + point.stage)}
											<span
												class="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold shadow {point.stage ===
												CURRENT
													? 'bg-surface-950 text-white'
													: 'border-2 border-surface-950 bg-white text-surface-950'}"
												title="{pageName(point.page)} — {point.stage === CURRENT
													? m.currentRisk()
													: m.residualRisk()}">{keyOf(point.page)}</span
											>
										{/each}
									</div>
								{/each}
							{/each}
							<div></div>
							{#each colDim.levels as colLevel (colLevel.ref_id)}
								<div
									class="pt-1 text-center text-xs text-surface-600-400"
									title={colLevel.description}
								>
									{colLevel.label}
								</div>
							{/each}
						</div>
						<p class="pt-1 text-center text-xs font-semibold text-surface-600-400">
							{colDim.label}
						</p>
					</div>
				</div>
			{:else}
				<div class="max-w-full overflow-x-auto">
					<table class="table text-sm">
						<thead>
							<tr>
								<th></th>
								<th></th>
								{#each rating.dimensions as dimension (dimension.ref_id)}<th>{dimension.label}</th
									>{/each}
								<th>{rating.label}</th>
							</tr>
						</thead>
						<tbody>
							{#each rows as row (row.urn)}
								{#each row.points as point, i (point.stage)}
									<tr>
										<td class="font-semibold">{i === 0 ? `${row.key}. ${row.name}` : ''}</td>
										<td class="text-xs text-surface-500">
											{point.stage === CURRENT ? m.currentRisk() : m.residualRisk()}
										</td>
										{#each rating.dimensions as dimension (dimension.ref_id)}
											<td>{dimLabel(dimension, point.dims[dimension.ref_id]?.level)}</td>
										{/each}
										<td>
											<span
												class="badge {onColor(point.level && levels[point.level]?.color)}"
												style="background-color: {(point.level && levels[point.level]?.color) ||
													'transparent'}">{(point.level && levels[point.level]?.label) || '—'}</span
											>
										</td>
									</tr>
								{/each}
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
			{#if map}
				<ul class="flex flex-col gap-2 text-sm">
					<li class="flex gap-4 text-xs text-surface-600-400">
						<span
							><span class="mr-1 inline-block h-3 w-3 rounded-full bg-surface-950"
							></span>{m.currentRisk()}</span
						>
						<span
							><span class="mr-1 inline-block h-3 w-3 rounded-full border-2 border-surface-950"
							></span>{m.residualRisk()}</span
						>
					</li>
					{#each rows as row (row.urn)}
						<li>
							<span class="font-semibold">{row.key}. {row.name}</span>
							<span class="mt-1 flex flex-wrap items-center gap-1 text-xs">
								{#each row.points as point, i (point.stage)}
									{#if i > 0}<span class="text-surface-500">→</span>{/if}
									<span
										class="badge {onColor(point.level && levels[point.level]?.color)}"
										style="background-color: {(point.level && levels[point.level]?.color) ||
											'transparent'}">{(point.level && levels[point.level]?.label) || '—'}</span
									>
								{/each}
							</span>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</div>
{/each}
