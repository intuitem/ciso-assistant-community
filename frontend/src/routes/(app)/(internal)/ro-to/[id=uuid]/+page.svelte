<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import { pageTitle } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { canPerformAction } from '$lib/utils/access-control';
	interface Props {
		data: PageData;
	}
	let { data }: Props = $props();

	const roto = data.data;

	let activeActivity: string | null = $state(null);
	page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		} else if (key === 'activity' && value === 'three') {
			activeActivity = 'three';
		}
	});

	const pertinenceColor: Record<string, string> = {
		undefined: 'bg-surface-200-800 text-surface-700-300',
		irrelevant: 'bg-green-200 text-green-700',
		partially_relevant: 'bg-yellow-200 text-yellow-700',
		fairly_relevant: 'bg-orange-200 text-orange-700',
		highly_relevant: 'bg-red-200 text-red-700'
	};

	const user = page.data.user;
	import { URL_MODEL_MAP } from '$lib/utils/crud';

	pageTitle.set(data.title);

	const model = URL_MODEL_MAP['ro-to'];
	const canEditObject = (roto): boolean =>
		canPerformAction({
			user,
			action: 'change',
			model: model.name,
			domain: roto.folder?.id
		});
</script>

<div class="card p-4 bg-surface-50-950 shadow-lg">
	<div class="flex flex-col space-y-4">
		<div class="flex justify-between">
			<Anchor
				href="/ebios-rm/{roto.ebios_rm_study.id}"
				label={roto.ebios_rm_study.str}
				class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
			>
				<i class="fa-solid fa-arrow-left"></i>
				<p class="">{m.goBackToEbiosRmStudy()}</p>
			</Anchor>
			{#if canEditObject(roto)}
				<Anchor
					href={`${page.url.pathname}/edit?activity=${activeActivity}&next=${page.url.pathname}?activity=${activeActivity}`}
					class="btn preset-filled-primary-500 h-fit"
				>
					<i class="fa-solid fa-pen-to-square mr-2" data-testid="edit-button"></i>
					{m.edit()}
				</Anchor>
			{/if}
		</div>
		<div
			id="activityOne"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center justify-center
                {activeActivity === 'one'
				? 'border-2 border-primary-500'
				: 'border-2 border-surface-300-700 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-surface-50-950 font-bold {activeActivity === 'one'
					? 'text-primary-500'
					: 'text-surface-600-400'}">{m.activityOne()}</span
			>
			<h1
				class="font-bold text-xl {activeActivity === 'one'
					? 'text-primary-500'
					: 'text-surface-600-400'}"
			>
				{m.ebiosWs2_1()}
			</h1>
			<div class="flex flex-row space-x-1 items-center">
				<p class="flex flex-col items-center">
					<span class="text-xs text-surface-600-400">{m.riskOrigin()}</span>
					<span class="font-bold">{safeTranslate(roto.risk_origin)}</span>
				</p>
				<span class="text-surface-600-400 font-bold text-lg px-2">/</span>
				<p class="flex flex-col items-center">
					<span class="text-xs text-surface-600-400">{m.targetObjective()}</span>
					<span class="font-bold">{roto.target_objective}</span>
				</p>
			</div>
		</div>
		<div
			id="activityTwo"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center
                {activeActivity === 'two'
				? 'border-2 border-primary-500'
				: 'border-2 border-surface-300-700 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-surface-50-950 font-bold {activeActivity === 'two'
					? 'text-primary-500'
					: 'text-surface-600-400'}">{m.activityTwo()}</span
			>
			<h1
				class="font-bold text-xl {activeActivity === 'two'
					? 'text-primary-500'
					: 'text-surface-600-400'}"
			>
				{m.ebiosWs2_2()}
			</h1>
			<div class="flex space-x-6">
				<p class="flex flex-col items-center">
					<span class="text-xs text-surface-600-400">{m.motivation()}</span>
					<span class="badge text-sm font-bold">{safeTranslate(roto.motivation)}</span>
				</p>
				<i class="fa-solid fa-xmark self-center"></i>
				<p class="flex flex-col items-center">
					<span class="text-xs text-surface-600-400">{m.resources()}</span>
					<span class="badge text-sm font-bold">{safeTranslate(roto.resources)}</span>
				</p>
				<i class="fa-solid fa-equals"></i>
				<p class="flex flex-col items-center">
					<span class="text-xs text-surface-600-400">{m.pertinence()}</span>
					<span class="badge text-sm font-bold {pertinenceColor[roto.pertinence]}"
						>{safeTranslate(roto.pertinence)}</span
					>
				</p>
			</div>
			<p>
				<span class="badge bg-violet-200 text-violet-700">{m.rotoActivity()}</span>
				<span>=</span>
				<span class="font-bold">{safeTranslate(roto.activity)}</span>
			</p>
		</div>
		<div
			id="activityThree"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center
                {activeActivity === 'three'
				? 'border-2 border-primary-500'
				: 'border-2 border-surface-300-700 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-surface-50-950 font-bold {activeActivity === 'three'
					? 'text-primary-500'
					: 'text-surface-600-400'}">{m.activityThree()}</span
			>
			<h1
				class="font-bold text-xl {activeActivity === 'three'
					? 'text-primary-500'
					: 'text-surface-600-400'}"
			>
				{m.ebiosWs2_3()}
			</h1>
			<p>
				{#if roto.is_selected}
					<span class="badge bg-green-200 text-green-700">{m.selected()}</span>
				{:else}
					<span class="badge bg-red-200 text-red-700">{m.notSelected()}</span>
				{/if}
			</p>
			<div class="w-full p-4 bg-surface-50-950 border rounded-md shadow-xs">
				<h3 class="font-semibold text-lg text-surface-700-300 flex items-center space-x-2">
					<i class="fa-solid fa-table text-surface-600-400 opacity-75"></i>
					<span>{m.fearedEvents()}</span>
				</h3>
				<ModelTable
					backgroundColor="bg-surface-50-950"
					regionBody="bg-surface-50-950"
					regionHeadCell="uppercase bg-surface-50-950 text-surface-700-300"
					source={data.table}
					URLModel="feared-events"
					baseEndpoint={'feared-events/?ro_to_couples=' + roto.id}
					pagination={false}
					search={false}
					hideFilters={true}
					fields={['name', 'assets', 'description', 'qualifications', 'gravity']}
				></ModelTable>
			</div>
			<div class="w-full p-4 bg-surface-50-950 border rounded-md shadow-xs">
				<h3 class="font-semibold text-lg text-surface-700-300 flex items-center space-x-2">
					<i class="fa-solid fa-eye text-surface-600-400 opacity-75"></i>
					<span>{m.justification()}</span>
				</h3>
				{#if roto.justification}
					<p class="text-surface-600-400">{roto.justification}</p>
				{:else}
					<p class="text-surface-600-400">{m.noJustification()}</p>
				{/if}
			</div>
		</div>
	</div>
</div>
