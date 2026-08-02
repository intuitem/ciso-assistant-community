<script lang="ts">
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { postureResultTailwindColorMap } from '$lib/utils/constants';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const RESULT_ORDER = ['pass', 'fail', 'error', 'not_applicable', 'not_checked'];
	const resultLabels: Record<string, string> = {
		pass: m.pass(),
		fail: m.fail(),
		not_applicable: m.notApplicable(),
		error: m.error(),
		not_checked: m.notChecked()
	};

	function passRate(counts: Record<string, number>): number | null {
		const applicable = (counts.pass ?? 0) + (counts.fail ?? 0);
		return applicable ? Math.round((100 * (counts.pass ?? 0)) / applicable) : null;
	}

	function onAssetChange(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		const url = new URL(page.url);
		if (value) url.searchParams.set('asset', value);
		else url.searchParams.delete('asset');
		goto(url, { invalidateAll: true });
	}

	function submitOnChange(event: Event) {
		const select = event.currentTarget as HTMLSelectElement;
		if (select.value) select.form?.requestSubmit();
	}

	let treeContainer: HTMLDivElement | undefined = $state();
	let sessionRunId = $state('');

	function setAll(open: boolean) {
		treeContainer
			?.querySelectorAll('details')
			.forEach((node) => ((node as HTMLDetailsElement).open = open));
	}
</script>

{#snippet countChips(counts: Record<string, number>)}
	<span class="flex items-center gap-2 text-xs text-surface-600-400">
		{#each RESULT_ORDER as key}
			{#if counts[key]}
				<span class="flex items-center gap-1">
					<span class="inline-block w-2.5 h-2.5 rounded-sm {postureResultTailwindColorMap[key]}"
					></span>
					{counts[key]}
				</span>
			{/if}
		{/each}
		{#if passRate(counts) != null}
			<span class="font-semibold">{passRate(counts)}%</span>
		{/if}
	</span>
{/snippet}

{#snippet nodeView(node: any, depth: number)}
	{#if node.children?.length}
		<details open={depth <= 1} class="group">
			<summary
				class="flex items-center gap-2 cursor-pointer rounded px-2 py-1.5 hover:bg-surface-100-900"
			>
				<i
					class="fa-solid fa-chevron-right text-xs text-surface-500 transition-transform group-open:rotate-90"
				></i>
				<span class="font-semibold whitespace-nowrap">{node.ref_id}</span>
				<span class="grow truncate" title={node.name}>{node.name ?? ''}</span>
				{@render countChips(node.counts)}
			</summary>
			<div class="ml-4 pl-3 border-l border-surface-200-800 space-y-0.5">
				{#each node.children as child (child.id)}
					{@render nodeView(child, depth + 1)}
				{/each}
			</div>
		</details>
	{:else}
		<div class="flex items-center gap-2 px-2 py-1 rounded hover:bg-surface-100-900">
			<span class="font-medium whitespace-nowrap">{node.ref_id}</span>
			<span class="grow truncate text-surface-700-300" title={node.description ?? node.name}>
				{node.name ?? ''}
			</span>
			{#if node.assessable}
				{#if data.selectedAsset}
					{#if node.current}
						<span
							class="inline-block w-3 h-3 rounded-sm shrink-0 {postureResultTailwindColorMap[
								node.current.result
							]}"
							title={[
								node.current.actual,
								node.current.expected ? `expected: ${node.current.expected}` : '',
								node.current.message
							]
								.filter(Boolean)
								.join(' — ') || resultLabels[node.current.result]}
						></span>
					{/if}
					<form
						method="POST"
						action="?/setResult"
						use:enhance={() =>
							async ({ result, update }) => {
								if (result.type === 'success' && result.data?.run_id)
									sessionRunId = String(result.data.run_id);
								await update({ reset: false });
							}}
					>
						<input type="hidden" name="ref_id" value={node.ref_id} />
						<input type="hidden" name="asset" value={data.selectedAsset} />
						<input type="hidden" name="run_id" value={node.current?.run_id ?? sessionRunId} />
						<select
							name="result"
							class="select w-40 py-1 text-sm"
							value={node.current?.result ?? ''}
							onchange={submitOnChange}
						>
							<option value="" disabled>--</option>
							{#each RESULT_ORDER as key}
								<option value={key}>{resultLabels[key]}</option>
							{/each}
						</select>
					</form>
				{:else}
					{@render countChips(node.counts)}
				{/if}
			{/if}
		</div>
	{/if}
{/snippet}

<div class="flex flex-col space-y-4">
	<div class="card p-4 bg-surface-50-950 shadow-xs flex items-center gap-4 flex-wrap">
		<Anchor
			href="/posture-assessments/{page.params.id}"
			class="anchor whitespace-nowrap"
			label={data.assessment.name}
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>{data.assessment.name}
		</Anchor>
		<h3 class="text-lg font-semibold grow">{m.treeView()}</h3>
		<div class="flex items-center gap-1">
			<button type="button" class="btn btn-sm preset-tonal" onclick={() => setAll(true)}>
				<i class="fa-solid fa-angles-down mr-1"></i>{m.expandAll()}
			</button>
			<button type="button" class="btn btn-sm preset-tonal" onclick={() => setAll(false)}>
				<i class="fa-solid fa-angles-up mr-1"></i>{m.collapseAll()}
			</button>
		</div>
		<label class="flex items-center gap-2 text-sm">
			{m.selectAsset()}
			<select class="select w-64 py-1" value={data.selectedAsset ?? ''} onchange={onAssetChange}>
				<option value="">{m.allAssets()}</option>
				{#each data.assets as asset (asset.id)}
					<option value={asset.id}>{asset.str}</option>
				{/each}
			</select>
		</label>
	</div>

	{#if !data.selectedAsset}
		<p class="text-sm text-surface-600-400 px-2">{m.selectAssetToEditHelp()}</p>
	{/if}

	<div class="card p-4 bg-surface-50-950 shadow-xs space-y-0.5" bind:this={treeContainer}>
		{#each data.tree as node (node.id)}
			{@render nodeView(node, 0)}
		{/each}
	</div>
</div>
