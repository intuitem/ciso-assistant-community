<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	type AttackPath = {
		id: string;
		name?: string;
		risk_origin?: string;
		target_objective?: string;
		stakeholders?: Array<{
			id: string;
			str: string;
			entity?: {
				id: string;
				name: string;
			};
		}>;
	};

	type FearedEvent = {
		id: string;
		name: string;
	};

	type FearedEventWithAssets = {
		id: string;
		name: string;
		assets: Array<{
			id: string;
			str: string;
		}>;
	};

	interface Props {
		attackPaths: AttackPath[];
		fearedEvents: FearedEvent[];
		fearedEventsWithAssets: FearedEventWithAssets[];
	}

	let { attackPaths, fearedEvents, fearedEventsWithAssets }: Props = $props();
</script>

<!-- Text-based attack path flows -->
<div class="mb-4 space-y-3 bg-surface-50-950 p-4 rounded-lg border border-surface-200-800">
	{#each attackPaths as path}
		<div class="text-sm border-l-4 border-primary-500 pl-3 py-2">
			{#if path.name}
				<div class="font-semibold text-surface-700-300 mb-2">{path.name}</div>
			{/if}
			<div class="flex flex-wrap items-center gap-2 font-mono text-xs">
				<span class="px-2 py-1 bg-red-100 text-red-800 rounded font-semibold">
					{safeTranslate(path.risk_origin) || 'Unknown RO'}
				</span>
				<i class="fa-solid fa-arrow-right text-surface-400-600"></i>

				<span class="px-2 py-1 bg-purple-100 text-purple-800 rounded font-semibold">
					{path.target_objective || 'Unknown TO'}
				</span>
				<i class="fa-solid fa-arrow-right text-surface-400-600"></i>

				{#if path.stakeholders && path.stakeholders.length > 0}
					<div class="flex flex-wrap items-center gap-2">
						{#each path.stakeholders as stakeholder}
							<span class="px-2 py-1 bg-amber-100 text-amber-800 rounded">
								{stakeholder.str}
								{#if stakeholder.entity}
									<span class="text-amber-600 font-semibold">
										({stakeholder.entity.name})
									</span>
								{/if}
							</span>
							{#if stakeholder !== path.stakeholders[path.stakeholders.length - 1]}
								<span class="text-surface-300-700">|</span>
							{/if}
						{/each}
					</div>
					<i class="fa-solid fa-arrow-right text-surface-400-600"></i>
				{/if}

				{#if fearedEvents && fearedEvents.length > 0}
					<div class="flex flex-wrap items-center gap-2">
						{#each fearedEvents as fe}
							<span class="px-2 py-1 bg-orange-100 text-orange-800 rounded">
								{fe.name}
							</span>
							{#if fe !== fearedEvents[fearedEvents.length - 1]}
								<span class="text-surface-300-700">|</span>
							{/if}
						{/each}
					</div>
					<i class="fa-solid fa-arrow-right text-surface-400-600"></i>
				{/if}

				{#if fearedEventsWithAssets && fearedEventsWithAssets.length > 0}
					{@const uniqueAssets = [
						...new Map(
							fearedEventsWithAssets.flatMap((fe) => fe.assets).map((a) => [a.id, a])
						).values()
					]}
					{#if uniqueAssets.length > 0}
						<div class="flex flex-wrap items-center gap-2">
							{#each uniqueAssets as asset}
								<span class="px-2 py-1 bg-cyan-100 text-cyan-800 rounded text-xs">
									{asset.str}
								</span>
							{/each}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{/each}
</div>

<!-- Legend -->
<div class="mb-6 bg-surface-50-950 p-3 rounded-lg border border-surface-200-800">
	<h4 class="text-xs font-semibold text-surface-600-400 mb-2">{m.legend()}:</h4>
	<div class="flex flex-wrap gap-3 text-xs">
		<span class="px-2 py-1 bg-red-100 text-red-800 rounded font-semibold">{m.riskOrigin()}</span>
		<span class="px-2 py-1 bg-purple-100 text-purple-800 rounded font-semibold"
			>{m.targetObjective()}</span
		>
		<span class="px-2 py-1 bg-amber-100 text-amber-800 rounded">{m.stakeholder()}</span>
		<span class="px-2 py-1 bg-orange-100 text-orange-800 rounded">{m.fearedEvent()}</span>
		<span class="px-2 py-1 bg-cyan-100 text-cyan-800 rounded">{m.asset()}</span>
	</div>
</div>
