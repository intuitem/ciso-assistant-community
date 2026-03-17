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

	interface BudgetData {
		count: number;
		count_with_cost: number;
		total_annual_cost: number;
		total_annual_cost_display: string;
		currency: string;
		by_status: StatusBucket[];
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
	<div class="bg-white p-4 shadow-sm rounded-lg mb-2">
		<div class="animate-pulse space-y-3">
			<div class="h-4 bg-gray-200 rounded w-1/4"></div>
			<div class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3">
				<div class="h-20 bg-gray-100 rounded-lg"></div>
				<div class="h-20 bg-gray-100 rounded-lg"></div>
				<div class="h-20 bg-gray-100 rounded-lg"></div>
			</div>
		</div>
	</div>
{:else if !error && budgetData}
	{#if budgetData.count === 0}
		<!-- Empty: no controls at all, don't show anything -->
	{:else if budgetData.count_with_cost === 0}
		<div class="bg-white p-4 shadow-sm rounded-lg mb-2">
			<p class="text-sm text-gray-400 italic">{m.noCostDataAvailable()}</p>
		</div>
	{:else}
		<div class="bg-white p-4 shadow-sm rounded-lg mb-2">
			<button
				class="flex items-center gap-2 w-full text-left"
				onclick={() => (collapsed = !collapsed)}
			>
				<i
					class="fa-solid fa-chevron-right text-xs text-gray-400 transition-transform duration-200 {collapsed
						? ''
						: 'rotate-90'}"
				></i>
				<i class="fa-solid fa-coins text-violet-600"></i>
				<span class="text-lg font-semibold text-gray-800">{m.budgetOverview()}</span>
				{#if collapsed}
					<span class="text-sm text-gray-500 ml-2">{budgetData.total_annual_cost_display}</span>
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
					<p class="text-xs text-gray-400 italic">
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
