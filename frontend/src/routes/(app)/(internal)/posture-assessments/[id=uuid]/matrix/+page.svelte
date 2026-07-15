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

	const cells = $derived.by(() => {
		const map = new Map();
		for (const row of data.posture?.results ?? []) {
			map.set(`${row.requirement.id}:${row.asset.id}`, row);
		}
		return map;
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
		<h3 class="text-lg font-semibold grow">{m.matrixEdit()}</h3>
		<Anchor
			href="/posture-assessments/{page.params.id}/runs/new"
			class="btn btn-sm preset-filled-primary-500"
			label={m.newManualRun()}
		>
			<i class="fa-solid fa-plus mr-1"></i>{m.newManualRun()}
		</Anchor>
	</div>

	<p class="text-sm text-surface-600-400 px-2">{m.fixCurrentValuesHelp()}</p>

	<div class="card p-4 bg-surface-50-950 shadow-xs overflow-x-auto">
		<table class="table-auto text-sm w-full">
			<thead>
				<tr>
					<th class="text-left px-2 py-1 sticky left-0 bg-surface-50-950 z-10"></th>
					{#each data.assets as asset (asset.id)}
						<th class="px-2 py-1 text-left whitespace-nowrap max-w-44 truncate" title={asset.str}>
							{asset.str}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each data.checks as check (check.id)}
					<tr class="border-t border-surface-200-800 hover:bg-surface-100-900">
						<td
							class="px-2 py-1 whitespace-nowrap sticky left-0 bg-surface-50-950 font-medium max-w-96 truncate"
							title="{check.ref_id} {check.name ?? ''}"
						>
							{check.ref_id}
							<span class="font-normal text-surface-600-400">
								{check.name?.length > 45 ? `${check.name.slice(0, 45)}…` : (check.name ?? '')}
							</span>
						</td>
						{#each data.assets as asset (asset.id)}
							{@const cell = cells.get(`${check.id}:${asset.id}`)}
							<td class="px-1 py-0.5">
								<form method="POST" action="?/setCell" use:enhance class="flex items-center gap-1">
									<input type="hidden" name="ref_id" value={check.ref_id} />
									<input type="hidden" name="asset" value={asset.id} />
									<input type="hidden" name="run_id" value={cell?.run_id ?? ''} />
									{#if cell}
										<span
											class="inline-block w-2.5 h-2.5 rounded-sm shrink-0 {postureResultTailwindColorMap[
												cell.result
											]}"
										></span>
									{:else}
										<span
											class="inline-block w-2.5 h-2.5 rounded-sm shrink-0 border border-dashed border-surface-300-700"
										></span>
									{/if}
									<select
										name="result"
										class="select w-28 py-0.5 text-xs"
										value={cell?.result ?? ''}
										onchange={submitOnChange}
									>
										<option value="" disabled>--</option>
										{#each RESULT_ORDER as key}
											<option value={key}>{resultLabels[key]}</option>
										{/each}
									</select>
								</form>
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
