<script lang="ts">
	import { page } from '$app/stores';
	import { breadcrumbObject } from '$lib/utils/stores';

	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud.js';
	const showRisks = true;
	export let data;
	const riskMatrix = data.data;
	breadcrumbObject.set(riskMatrix);
</script>

<div class="flex flex-row justify-between">
	<div class="flex flex-col space-y-2">
		{#each Object.entries(riskMatrix).filter(([key, _]) => key !== 'id' && key !== 'json_definition' && key !== 'is_enabled') as [key, value]}
			<div class="flex flex-col">
				<div class="text-sm font-medium text-gray-800 capitalize-first">
					{key.replace('_', ' ')}
				</div>
				<ul class="text-sm">
					<li class="text-gray-600 list-none">
						{#if value}
							{#if Array.isArray(value)}
								<ul>
									{#each value as val}
										<li>
											{#if val.str && val.id}
												{@const itemHref = `/${
													URL_MODEL_MAP[data.urlModel]['foreignKeyFields']?.find(
														(item) => item.field === key
													)?.urlModel
												}/${val.id}`}
												<a href={itemHref} class="anchor">{val.str}</a>
											{:else}
												{value}
											{/if}
										</li>
									{/each}
								</ul>
							{:else if value.id}
								{@const itemHref = `/${
									URL_MODEL_MAP['risk-matrices']['foreignKeyFields']?.find(
										(item) => item.field === key
									)?.urlModel
								}/${value.id}`}
								<a href={itemHref} class="anchor">{value.str}</a>
							{:else}
								{value.str ?? value}
							{/if}
						{:else}
							--
						{/if}
					</li>
				</ul>
			</div>
		{/each}
	</div>
</div>

<RiskMatrix {riskMatrix} {showRisks} wrapperClass="mt-8" />
