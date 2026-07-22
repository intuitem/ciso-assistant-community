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

	let values: Record<string, string> = $state({ ...data.prefill });
	let bulkValue = $state('pass');

	$effect(() => {
		values = { ...data.prefill };
	});

	const filled = $derived(Object.values(values).filter(Boolean).length);

	function applyToUnset() {
		for (const check of data.checks) {
			if (!values[check.ref_id]) values[check.ref_id] = bulkValue;
		}
	}

	// searchable asset picker (whole catalog — saving auto-enrolls into scope)
	let pickerOpen = $state(false);
	let pickerQuery = $state('');
	let pickerResults: any[] = $state([]);

	async function searchAssets() {
		if (!pickerQuery && data.assets.length) {
			pickerResults = data.assets.map((a: any) => ({ id: a.id, name: a.str }));
			return;
		}
		const res = await fetch(`/assets?search=${encodeURIComponent(pickerQuery)}&limit=10`);
		const body = await res.json();
		pickerResults = body.results ?? body;
	}

	function pickAsset(id: string) {
		pickerOpen = false;
		const url = new URL(page.url);
		url.searchParams.set('asset', id);
		goto(url, { invalidateAll: true });
	}
</script>

<div class="flex flex-col space-y-4">
	<div class="card p-4 bg-surface-50-950 shadow-xs flex items-center gap-4 flex-wrap">
		<Anchor
			href="/posture-assessments/{page.params.id}"
			class="anchor whitespace-nowrap"
			label={data.assessment.name}
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>{data.assessment.name}
		</Anchor>
		<h3 class="text-lg font-semibold grow">{m.newManualRun()}</h3>
		<div class="flex items-center gap-2 text-sm relative">
			<span>{m.selectAsset()}</span>
			<button
				type="button"
				class="btn preset-tonal w-64 justify-between"
				onclick={() => {
					pickerOpen = !pickerOpen;
					if (pickerOpen) {
						pickerQuery = '';
						searchAssets();
					}
				}}
			>
				<span class="truncate">{data.selectedAssetName ?? '--'}</span>
				<i class="fa-solid fa-chevron-down text-xs"></i>
			</button>
			{#if pickerOpen}
				<div
					class="absolute right-0 top-full mt-1 card bg-surface-50-950 shadow-lg p-3 w-72 z-20 space-y-2"
				>
					<input
						type="search"
						class="input w-full py-1 text-sm"
						placeholder={m.searchPlaceholder()}
						bind:value={pickerQuery}
						oninput={searchAssets}
					/>
					<div class="max-h-64 overflow-y-auto">
						{#each pickerResults as candidate (candidate.id)}
							<button
								type="button"
								class="w-full text-left px-2 py-1 text-sm rounded hover:bg-surface-100-900"
								onclick={() => pickAsset(candidate.id)}
							>
								{candidate.folder?.str ? `${candidate.folder.str}/` : ''}{candidate.name ??
									candidate.str}
							</button>
						{:else}
							<p class="text-xs text-surface-600-400">{m.noEntriesFound()}</p>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>

	{#if data.prefillDropped > 0}
		<p class="text-sm text-amber-600 dark:text-amber-400 px-2">
			<i class="fa-solid fa-triangle-exclamation mr-1"></i>
			{m.clonePrefillDropped({ count: data.prefillDropped })}
		</p>
	{/if}

	{#if !data.selectedAsset}
		<p class="text-sm text-surface-600-400 px-2">{m.selectAssetToEditHelp()}</p>
	{:else}
		<form method="POST" action="?/saveRun" use:enhance>
			<input type="hidden" name="asset" value={data.selectedAsset} />
			<div class="card p-4 bg-surface-50-950 shadow-xs space-y-3">
				<div class="flex items-center gap-3 flex-wrap border-b border-surface-200-800 pb-3">
					<p class="text-sm text-surface-600-400 grow">{m.newManualRunHelp()}</p>
					<div class="flex items-center gap-2 text-sm">
						<select class="select w-36 py-1" bind:value={bulkValue}>
							{#each RESULT_ORDER as key}
								<option value={key}>{resultLabels[key]}</option>
							{/each}
						</select>
						<button type="button" class="btn btn-sm preset-tonal" onclick={applyToUnset}>
							<i class="fa-solid fa-fill-drip mr-1"></i>{m.applyToUnset()}
						</button>
					</div>
					<button type="submit" class="btn preset-filled-primary-500" disabled={filled === 0}>
						<i class="fa-solid fa-floppy-disk mr-2"></i>{m.save()} ({filled}/{data.checks.length})
					</button>
				</div>
				<div class="space-y-0.5">
					{#each data.checks as check (check.id)}
						<div class="flex items-center gap-2 px-2 py-1 rounded hover:bg-surface-100-900">
							<span class="font-medium whitespace-nowrap">{check.ref_id}</span>
							<span
								class="grow truncate text-surface-700-300"
								title={check.description ?? check.name}
							>
								{check.name ?? ''}
							</span>
							{#if values[check.ref_id]}
								<span
									class="inline-block w-2.5 h-2.5 rounded-sm shrink-0 {postureResultTailwindColorMap[
										values[check.ref_id]
									]}"
								></span>
							{/if}
							<select
								name="result:{check.ref_id}"
								class="select w-40 py-1 text-sm"
								bind:value={values[check.ref_id]}
							>
								<option value="">--</option>
								{#each RESULT_ORDER as key}
									<option value={key}>{resultLabels[key]}</option>
								{/each}
							</select>
						</div>
					{/each}
				</div>
			</div>
		</form>
	{/if}
</div>
