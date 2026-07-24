<script lang="ts">
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { enhance } from '$app/forms';
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

	const byAsset = $derived.by(() => {
		const groups = new Map<string, { name: string; rows: any[] }>();
		for (const row of data.results) {
			const group = groups.get(row.asset.id) ?? { name: row.asset.str, rows: [] };
			group.rows.push(row);
			groups.set(row.asset.id, group);
		}
		return [...groups.entries()].map(([id, group]) => ({ id, ...group }));
	});

	function submitOnChange(event: Event) {
		const select = event.currentTarget as HTMLSelectElement;
		if (select.value) select.form?.requestSubmit();
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
		<h3 class="text-lg font-semibold grow">{m.runDetail()}</h3>
		<div class="flex items-center gap-4 text-sm text-surface-600-400 flex-wrap">
			<span
				><i class="fa-solid fa-calendar mr-1"></i>
				{new Date(data.run.started_at).toLocaleString()}</span
			>
			<span><i class="fa-solid fa-wrench mr-1"></i>{data.run.tool || '--'}</span>
			<span class="badge preset-tonal-secondary">{data.run.source}</span>
			<span class="text-green-600 dark:text-green-400">{m.pass()}: {data.run.passed}</span>
			<span class={data.run.failed ? 'text-red-600 dark:text-red-400' : ''}>
				{m.fail()}: {data.run.failed}
			</span>
		</div>
	</div>

	<p class="text-sm text-surface-600-400 px-2">{m.runEditHelp()}</p>

	{#each byAsset as group (group.id)}
		<div class="card p-4 bg-surface-50-950 shadow-xs space-y-2">
			<div class="flex items-center justify-between">
				<h4 class="font-semibold">{group.name}</h4>
				<Anchor
					href="/posture-assessments/{page.params.id}/runs/new?from={page.params
						.rid}&asset={group.id}"
					class="btn btn-sm preset-filled-primary-500"
					label={m.cloneAsNewRun()}
				>
					<i class="fa-solid fa-copy mr-1"></i>{m.cloneAsNewRun()}
				</Anchor>
			</div>
			<div class="space-y-0.5">
				{#each group.rows as row (row.id)}
					<div class="flex items-center gap-2 px-2 py-1 rounded hover:bg-surface-100-900">
						<span class="font-medium whitespace-nowrap">{row.requirement.ref_id}</span>
						<span class="grow truncate text-surface-700-300" title={row.requirement.name}>
							{row.requirement.name ?? ''}
						</span>
						{#if row.actual || row.message}
							<span
								class="text-xs text-surface-500 truncate max-w-64"
								title={[row.actual, row.expected, row.message].filter(Boolean).join(' — ')}
							>
								{row.actual || row.message}
							</span>
						{/if}
						<span
							class="inline-block w-2.5 h-2.5 rounded-sm shrink-0 {postureResultTailwindColorMap[
								row.result
							]}"
						></span>
						<form method="POST" action="?/setResult" use:enhance>
							<input type="hidden" name="ref_id" value={row.requirement.ref_id} />
							<input type="hidden" name="asset" value={group.id} />
							<select
								name="result"
								class="select w-36 py-0.5 text-sm"
								value={row.result}
								aria-label="{row.requirement.ref_id} — {m.result()}"
								onchange={submitOnChange}
							>
								{#each RESULT_ORDER as key}
									<option value={key}>{resultLabels[key]}</option>
								{/each}
							</select>
						</form>
					</div>
				{/each}
			</div>
		</div>
	{/each}
</div>
