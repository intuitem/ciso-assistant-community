<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import SimpleCard from './SimpleCard.svelte';
	import CardGroup from './CardGroup.svelte';

	interface Props {
		budgetEndpoint: string;
	}

	let { budgetEndpoint }: Props = $props();

	interface StatusBucket {
		status: string;
		count: number;
		total: number;
		total_display: string;
	}

	interface CostLeg {
		fixed_cost: number;
		fixed_cost_display: string;
		people_days: number;
	}

	interface BudgetData {
		count: number;
		count_with_cost: number;
		total_annual_cost: number;
		total_annual_cost_display: string;
		currency: string;
		by_status: StatusBucket[];
		cost_breakdown?: {
			build: CostLeg;
			run: CostLeg;
		};
	}

	let budgetData: BudgetData | null = $state(null);
	let loading = $state(true);
	let error = $state(false);
	let collapsed = $state(false);

	async function fetchBudget() {
		try {
			const res = await fetch(budgetEndpoint);
			if (!res.ok) {
				error = true;
				return;
			}
			budgetData = await res.json();
		} catch {
			error = true;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		fetchBudget();
	});
</script>

{#if loading}
	<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg mb-2">
		<div class="animate-pulse space-y-3">
			<div class="h-4 bg-surface-200-800 rounded w-1/4"></div>
			<div class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3">
				<div class="h-20 bg-surface-100-900 rounded-lg"></div>
				<div class="h-20 bg-surface-100-900 rounded-lg"></div>
				<div class="h-20 bg-surface-100-900 rounded-lg"></div>
			</div>
		</div>
	</div>
{:else if !error && budgetData}
	{#if budgetData.count === 0}
		<!-- Empty: no controls at all, don't show anything -->
	{:else if budgetData.count_with_cost === 0}
		<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg mb-2">
			<p class="text-sm text-surface-500 italic">{m.noCostDataAvailable()}</p>
		</div>
	{:else}
		<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg mb-2">
			<button
				class="flex items-center gap-2 w-full text-left"
				onclick={() => (collapsed = !collapsed)}
			>
				<i
					class="fa-solid fa-chevron-right text-xs text-surface-500 transition-transform duration-200 {collapsed
						? ''
						: 'rotate-90'}"
				></i>
				<i class="fa-solid fa-coins text-violet-600"></i>
				<span class="text-lg font-semibold text-surface-800-200">{m.budgetOverview()}</span>
				{#if collapsed}
					<span class="text-sm text-surface-600-400 ml-2"
						>{budgetData.total_annual_cost_display}</span
					>
				{/if}
			</button>
			{#if !collapsed}
				<div class="mt-3 space-y-3">
					<div class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3">
						<SimpleCard
							count={budgetData.total_annual_cost_display}
							label={m.totalAnnualCost()}
							emphasis={true}
							raw={true}
						/>
						{#each budgetData.by_status.filter((b) => b.total > 0) as bucket}
							<SimpleCard
								count={bucket.total_display}
								label={safeTranslate(bucket.status)}
								raw={true}
							/>
						{/each}
					</div>
					{#if budgetData.cost_breakdown}
						{@const cb = budgetData.cost_breakdown}
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
							{#each [{ leg: cb.build, label: m.buildCosts() }, { leg: cb.run, label: m.runCosts() }] as entry}
								<div class="border border-surface-200-800 rounded-lg p-3">
									<div
										class="text-xs font-semibold text-surface-600-400 uppercase tracking-wide mb-2"
									>
										{entry.label}
									</div>
									<div class="flex items-baseline justify-between gap-3">
										<div class="flex flex-col">
											<span class="text-xl font-bold text-surface-800-200 leading-none"
												>{entry.leg.fixed_cost_display}</span
											>
											<span class="text-xs text-surface-600-400 mt-1">{m.fixedCost()}</span>
										</div>
										<div class="flex flex-col text-right">
											<span class="text-xl font-bold text-surface-800-200 leading-none"
												>{entry.leg.people_days.toLocaleString()}</span
											>
											<span class="text-xs text-surface-600-400 mt-1">{m.peopleDays()}</span>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
					<p class="text-xs text-surface-500 italic">
						{m.budgetOverviewHint({
							x: String(budgetData.count_with_cost),
							y: String(budgetData.count)
						})}
					</p>
				</div>
			{/if}
		</div>
	{/if}
{/if}
