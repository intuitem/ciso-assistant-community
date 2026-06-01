<script lang="ts">
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { formatDate } from '$lib/utils/datetime';
	import type { TreeViewNode } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import TreeExpandCollapseToggle from '$lib/components/TreeView/TreeExpandCollapseToggle.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Track data reactively — SvelteKit reuses this component instance when
	// navigating between two /frameworks/{id} URLs, so plain `const` snapshots
	// would point at the previous framework after the data prop updates.
	let fw = $derived(data.framework);
	let tree = $derived(data.tree);
	let expandedNodes: string[] = $state([]);

	function transformToTreeView(nodes) {
		return nodes.map(([id, node]) => {
			node.id = id;
			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: node,
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}
	let treeViewNodes = $derived(transformToTreeView(Object.entries(tree)) as TreeViewNode[]);

	// Node ids in the previous tree don't match the new tree on framework
	// change, so wipe the expansion state to avoid a confusing half-open panel.
	$effect(() => {
		void fw.id;
		expandedNodes = [];
	});

	function assessableNodesCount(nodes: TreeViewNode[]): number {
		let count = 0;
		for (const node of nodes) {
			if (node.contentProps.assessable) count++;
			if (node.children) count += assessableNodesCount(node.children);
		}
		return count;
	}

	let scoreScale = $derived(fw.scores_definition?.scale ?? fw.scores_definition ?? []);
	let hasScoreScale = $derived(Array.isArray(scoreScale) && scoreScale.length > 0);
	let igs = $derived(fw.implementation_groups_definition ?? []);
	let hasIgs = $derived(Array.isArray(igs) && igs.length > 0);
	let hasScoreRange = $derived(
		fw.min_score !== null &&
			fw.min_score !== undefined &&
			fw.max_score !== null &&
			fw.max_score !== undefined
	);
</script>

<div class="flex flex-col space-y-4">
	<!-- Hero card -->
	<div class="card px-6 py-5 bg-white shadow-lg flex flex-row justify-between gap-6 items-start">
		<div class="flex-1 min-w-0">
			<div
				class="flex flex-wrap items-center gap-2 text-xs uppercase tracking-wide text-gray-500 mb-1"
			>
				{#if fw.provider}
					<span class="font-semibold">{fw.provider}</span>
				{/if}
				{#if fw.ref_id}
					{#if fw.provider}<span class="text-gray-300">·</span>{/if}
					<span class="font-mono normal-case text-gray-600">{fw.ref_id}</span>
				{/if}
				{#if fw.is_published}
					<span class="badge preset-tonal-success normal-case text-[10px] ml-1"
						>{m.published()}</span
					>
				{/if}
				{#if fw.has_update}
					<a
						href="/libraries?is_update=true"
						class="badge preset-tonal-warning normal-case text-[10px] ml-1 hover:preset-tonal-warning/80"
						title={m.updateAvailable()}
					>
						<i class="fa-solid fa-circle-up mr-1"></i>
						{m.updateAvailable()}
					</a>
				{/if}
			</div>

			<h1 class="text-2xl font-semibold text-gray-900">{fw.name}</h1>

			{#if fw.description}
				<div class="prose prose-sm max-w-none mt-3 text-gray-700">
					<MarkdownRenderer content={fw.description} />
				</div>
			{/if}
		</div>

		<div class="flex flex-col gap-2 shrink-0 w-64">
			<a class="btn preset-filled-primary-500" href="/frameworks/{fw.id}/report/">{m.insights()}</a>
			<a class="btn preset-filled-primary-500" href="/frameworks/{fw.id}/excel-template/">
				{m.downloadExcelTemplate()}
			</a>
			<p class="text-xs text-gray-500 leading-snug mt-1">
				{m.frameworkActionsHelp({ dataWizard: m.dataWizard() })}
			</p>
		</div>
	</div>

	<!-- Grouped metadata -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<!-- Identity -->
		<div class="card px-6 py-4 bg-white shadow">
			<h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
				{m.identity()}
			</h3>
			<dl class="space-y-3 text-sm">
				{#if fw.folder?.id}
					<div class="flex flex-col">
						<dt class="text-xs text-gray-500">{m.domain()}</dt>
						<dd>
							<Anchor href="/folders/{fw.folder.id}" class="anchor">{fw.folder.str}</Anchor>
						</dd>
					</div>
				{/if}
				{#if fw.library?.id}
					<div class="flex flex-col">
						<dt class="text-xs text-gray-500">{m.library()}</dt>
						<dd>
							<Anchor href="/loaded-libraries/{fw.library.id}" class="anchor"
								>{fw.library.str}</Anchor
							>
						</dd>
					</div>
				{/if}
				{#if fw.urn}
					<div class="flex flex-col">
						<dt class="text-xs text-gray-500">{m.urn()}</dt>
						<dd class="font-mono text-xs text-gray-700 break-all">{fw.urn}</dd>
					</div>
				{/if}
			</dl>
		</div>

		<!-- Scoring -->
		<div class="card px-6 py-4 bg-white shadow">
			<h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
				{m.scoring()}
			</h3>
			<dl class="space-y-3 text-sm">
				{#if hasScoreRange}
					<div class="flex flex-col">
						<dt class="text-xs text-gray-500">{m.scoreRange()}</dt>
						<dd class="font-mono">{fw.min_score}–{fw.max_score}</dd>
					</div>
				{/if}
				{#if hasScoreScale}
					<div class="flex flex-col">
						<dt class="text-xs text-gray-500">{m.scoreScale()}</dt>
						<dd>
							<ul class="space-y-0.5 text-xs">
								{#each scoreScale as level}
									<li>
										<span class="font-mono text-gray-600">{level.value ?? level.score}</span>
										· {level.name}{level.description ? ` — ${level.description}` : ''}
									</li>
								{/each}
							</ul>
						</dd>
					</div>
				{/if}
				{#if hasIgs}
					<div class="flex flex-col">
						<dt class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
							{m.implementationGroups()}
						</dt>
						<dd>
							<ul class="space-y-0.5 text-xs">
								{#each igs as ig}
									<li>
										<span class="font-mono text-gray-600">{ig.ref_id ?? ig.id}</span>
										· {ig.name}{ig.description ? ` — ${ig.description}` : ''}
									</li>
								{/each}
							</ul>
						</dd>
					</div>
				{/if}
				{#if !hasScoreRange && !hasScoreScale && !hasIgs}
					<div class="text-xs text-gray-400 italic">—</div>
				{/if}
			</dl>
		</div>

		<!-- Lifecycle -->
		<div class="card px-6 py-4 bg-white shadow">
			<h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
				{m.lifecycle()}
			</h3>
			<dl class="space-y-3 text-sm">
				{#if fw.updated_at}
					<div class="flex flex-col">
						<dt class="text-xs text-gray-500">{m.updatedAt()}</dt>
						<dd>{formatDate(new Date(fw.updated_at), true, getLocale())}</dd>
					</div>
				{/if}
				<div class="flex flex-col">
					<dt class="text-xs text-gray-500">{m.published()}</dt>
					<dd>
						<span
							class="badge {fw.is_published
								? 'preset-tonal-success'
								: 'preset-tonal-surface'} text-xs"
						>
							{fw.is_published ? '✓' : '—'}
						</span>
					</dd>
				</div>
				{#if fw.has_update}
					<div class="flex flex-col">
						<dt class="text-xs text-gray-500">{m.updateAvailable()}</dt>
						<dd>
							<a href="/libraries?is_update=true" class="badge preset-tonal-warning text-xs">
								<i class="fa-solid fa-circle-up mr-1"></i>
								{m.updateAvailable()}
							</a>
						</dd>
					</div>
				{/if}
			</dl>
		</div>
	</div>

	<!-- Requirements tree -->
	<div class="card px-6 py-4 bg-white shadow-lg">
		<div class="flex items-center justify-between">
			<h4 class="h4 flex items-center font-semibold">
				{m.associatedRequirements()}
				<span class="badge preset-tonal-primary ml-1">
					{assessableNodesCount(treeViewNodes)}
				</span>
			</h4>
			<TreeExpandCollapseToggle nodes={treeViewNodes} bind:expandedNodes />
		</div>
		<RecursiveTreeView nodes={treeViewNodes} bind:expandedNodes hover="hover:bg-initial" />
	</div>
</div>
