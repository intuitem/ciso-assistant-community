<script lang="ts">
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import * as m from '$paraglide/messages';
	import type { TreeViewNode } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	export let data: PageData;

	const tree = data.tree;

	function transformToTreeView(nodes) {
		return nodes.map(([id, node]) => {
			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: node,
				// lead: TreeViewItemLead,
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[] = transformToTreeView(Object.entries(tree));

	function assessableNodesCount(nodes: TreeViewNode[]): number {
		let count = 0;
		for (const node of nodes) {
			if (node.contentProps.assessable) {
				count++;
			}
			if (node.children) {
				count += assessableNodesCount(node.children);
			}
		}
		return count;
	}
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg">
		<div class="flex flex-col space-y-2">
			{#each Object.entries(data.framework).filter(([key, _]) => key !== 'id' && key !== 'created_at' && key !== 'reference_controls') as [key, value]}
				<div class="flex flex-col">
					<div class="text-sm font-medium text-gray-800 capitalize-first">
						{#if key === 'urn'}
							{m.urn()}
						{:else}
							{safeTranslate(key)}
						{/if}
					</div>
					<ul class="text-sm">
						<li class="text-gray-600 list-none">
							{#if value}
								{#if key === 'library'}
									{@const itemHref = `/libraries/${value.id}?loaded`}
									<Anchor href={itemHref} class="anchor">{value.str}</Anchor>
								{:else if key === 'scores_definition'}
									{#each Object.entries(value) as [key, definition]}
										<div>
											{definition.score}.
											{definition.name}{definition.description ? `: ${definition.description}` : ''}
										</div>
									{/each}
								{:else if key === 'implementation_groups_definition'}
									{#each Object.entries(value) as [_, definition]}
										<div>
											** {definition.ref_id} **
											{definition.name}
											{#if Object.hasOwn(definition, 'description') && definition.description}
												: {definition.description}
											{/if}
										</div>
									{/each}
								{:else if Array.isArray(value)}
									<ul>
										{#each value as val}
											<li>
												{#if val.str && val.id}
													{@const itemHref = `/${
														URL_MODEL_MAP[data.urlModel]['foreignKeyFields']?.find(
															(item) => item.field === key
														)?.urlModel
													}/${val.id}`}
													<Anchor href={itemHref} class="anchor">{val.str}</Anchor>
												{:else}
													{value}
												{/if}
											</li>
										{/each}
									</ul>
								{:else if value.str && value.id}
									{@const itemHref = `/${
										URL_MODEL_MAP['frameworks']['foreignKeyFields']?.find(
											(item) => item.field === key
										)?.urlModel
									}/${value.id}`}
									<Anchor href={itemHref} class="anchor">{value.str}</Anchor>
								{:else}
									{value.str ?? value}
								{/if}
							{:else if value === 0 && key === 'min_score'}
								{value}
							{:else}
								--
							{/if}
						</li>
					</ul>
				</div>
			{/each}
		</div>
	</div>

	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg">
		<h4 class="h4 flex items-center font-semibold">
			{m.associatedRequirements()}
			<span class="badge variant-soft-primary ml-1">
				{assessableNodesCount(treeViewNodes)}
			</span>
		</h4>
		<RecursiveTreeView nodes={treeViewNodes} hover="hover:bg-initial" />
	</div>
</div>
