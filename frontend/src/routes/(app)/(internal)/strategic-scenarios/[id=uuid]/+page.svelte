<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import AttackPathGraph from '$lib/components/EbiosRM/AttackPathGraph.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-gray-50 shadow-xs grow">
				<h3 class="text-lg font-semibold mb-4">
					<i class="fa-solid fa-route mr-2"></i>
					{m.attackPaths()}
				</h3>
				{#key data.attackPaths}
					{#if data.attackPaths && data.attackPaths.length > 0}
						<!-- Text-based attack path flows -->
						<div class="mb-6 space-y-3 bg-white p-4 rounded-lg border border-gray-200">
							<h4 class="text-sm font-semibold text-gray-700 mb-3">Attack Path Flows:</h4>
							{#each data.attackPaths as path}
								<div class="text-sm border-l-4 border-primary-500 pl-3 py-2">
									<div class="flex flex-wrap items-center gap-2 font-mono text-xs">
										<span class="px-2 py-1 bg-red-100 text-red-800 rounded font-semibold">
											{safeTranslate(path.risk_origin) || 'Unknown RO'}
										</span>
										<i class="fa-solid fa-arrow-right text-gray-400"></i>

										<span class="px-2 py-1 bg-purple-100 text-purple-800 rounded font-semibold">
											{path.target_objective || 'Unknown TO'}
										</span>
										<i class="fa-solid fa-arrow-right text-gray-400"></i>

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
														<span class="text-gray-300">|</span>
													{/if}
												{/each}
											</div>
											<i class="fa-solid fa-arrow-right text-gray-400"></i>
										{/if}

										{#if data.fearedEventsWithAssets && data.fearedEventsWithAssets.length > 0}
											<div class="flex flex-wrap items-center gap-2">
												{#each data.fearedEventsWithAssets as fe}
													{#each fe.assets as asset}
														<span class="px-2 py-1 bg-cyan-100 text-cyan-800 rounded text-xs">
															{asset.str}
														</span>
													{/each}
												{/each}
											</div>
											<i class="fa-solid fa-arrow-right text-gray-400"></i>
										{/if}

										{#if data.data.feared_events && data.data.feared_events.length > 0}
											<div class="flex flex-wrap items-center gap-2">
												{#each data.data.feared_events as fe}
													<span class="px-2 py-1 bg-green-100 text-green-800 rounded">
														{fe.str}
													</span>
													{#if fe !== data.data.feared_events[data.data.feared_events.length - 1]}
														<span class="text-gray-300">|</span>
													{/if}
												{/each}
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>

						<!-- Graph visualization -->
						<AttackPathGraph
							attackPaths={data.attackPaths}
							fearedEvents={data.fearedEventsWithAssets || []}
							height="600px"
						/>
					{:else}
						<div class="flex flex-col items-center justify-center py-12 text-center">
							<i class="fa-solid fa-diagram-project text-gray-300 text-6xl mb-4"></i>
							<p class="text-gray-500 text-sm">{m.noAttackPathsDefined()}</p>
							<p class="text-gray-400 text-xs mt-2">
								Add attack paths to visualize the strategic scenario
							</p>
						</div>
					{/if}
				{/key}
			</div>
		</div>
	{/snippet}
</DetailView>
