<script lang="ts">
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';

	export let data: PageData;

	import { breadcrumbObject } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { URL_MODEL_MAP, getModelInfo } from '$lib/utils/crud';
	breadcrumbObject.set(data.data);

	import AuditTableMode from '../../compliance-assessments/[id=uuid]/table-mode/+page.svelte';
	import { TreeView, TreeViewItem } from '@skeletonlabs/skeleton';

	import { page } from '$app/stores';
	import { goto, preloadData, pushState } from '$app/navigation';

	$: console.log($page.state.auditTableMode);
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg w-full">
		<div class="flex flex-col space-y-2 whitespace-pre-line w-1/5 pr-1">
			{#each Object.entries(data.data).filter( ([key, _]) => ['entity', 'name', 'description', 'project', 'compliance_assessment', 'authors', 'reviewers', 'status'].includes(key) ) as [key, value]}
				<div class="flex flex-col">
					<div
						class="text-sm font-medium text-gray-800 capitalize-first"
						data-testid={key.replaceAll('_', '-') + '-field-title'}
					>
						{#if key === 'urn'}
							{m.urn()}
						{:else}
							{safeTranslate(key)}
						{/if}
					</div>
					<ul class="text-sm">
						<li
							class="text-gray-600 list-none"
							data-testid={key.replaceAll('_', '-') + '-field-value'}
						>
							{#if value}
								{#if Array.isArray(value)}
									<ul>
										{#each value as val}
											<li>
												{#if val.str && val.id}
													{@const itemHref = `/${
														getModelInfo(data.urlModel).foreignKeyFields?.find(
															(item) => item.field === key
														)?.urlModel
													}/${val.id}`}
													<a href={itemHref} class="anchor">{val.str}</a>
												{:else}
													{val}
												{/if}
											</li>
										{/each}
									</ul>
								{:else if value.str && value.id}
									{@const itemHref = `/${
										URL_MODEL_MAP['compliance-assessments']['foreignKeyFields']?.find(
											(item) => item.field === key
										)?.urlModel
									}/${value.id}`}
									<a href={itemHref} class="anchor">{value.str}</a>
								{:else}
									{safeTranslate(value)}
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

	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg w-full">
		<TreeView>
			<TreeViewItem
				on:toggle={async (e) => {
					e.preventDefault();
					const href = `/compliance-assessments/${data.data.compliance_assessment.id}/table-mode`;
					const result = await preloadData(href);
					if (result.type === 'loaded' && result.status === 200) {
						pushState(href, { auditTableMode: result.data });
					} else {
						// Something went wrong, try navigating
						goto(href);
					}
				}}
				>(audit table mode)
				<svelte:fragment slot="children">
					{#if Object.hasOwn($page.state, 'auditTableMode')}
						<AuditTableMode data={$page.state.auditTableMode} />
					{/if}
				</svelte:fragment>
			</TreeViewItem>
		</TreeView>
	</div>
</div>
