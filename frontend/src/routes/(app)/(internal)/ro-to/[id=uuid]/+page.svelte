<script lang="ts">
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	import { page } from '$app/stores';
	import { pageTitle } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	export let data: PageData;

	const roto = data.data;

	pageTitle.set(roto.risk_origin + ' - ' + roto.target_objective);

	let activeActivity: string | null = null;
	$page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		} else if (key === 'activity' && value === 'three') {
			activeActivity = 'three';
		}
	});

	const pertinenceColor = {
		undefined: 'bg-gray-200 text-gray-700',
		irrelevant: 'bg-green-200 text-green-700',
		'partially relevant': 'bg-yellow-200 text-yellow-700',
		fairly_relevant: 'bg-orange-200 text-orange-700',
		higly_relevant: 'bg-red-200 text-red-700'
	};
</script>

<div class="card p-4 bg-white shadow-lg">
	<div class="flex flex-col space-y-4">
		<div class="flex justify-between">
			<Anchor
				href="/ebios-rm/{roto.ebios_rm_study.id}"
				label={roto.ebios_rm_study.str}
				class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
			>
				<i class="fa-solid fa-arrow-left" />
				<p class="">{m.goBackToEbiosRmStudy()}</p>
			</Anchor>
			<Anchor
				href={`${$page.url.pathname}/edit?activity=${activeActivity}&next=${$page.url.pathname}?activity=${activeActivity}`}
				class="btn variant-filled-primary h-fit"
			>
				<i class="fa-solid fa-pen-to-square mr-2" data-testid="edit-button" />
				{m.edit()}
			</Anchor>
		</div>
		<div
			id="activityOne"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center justify-center
                {activeActivity === 'one'
				? 'border-2 border-primary-500'
				: 'border-2 border-gray-300 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-white font-bold {activeActivity === 'one'
					? 'text-primary-500'
					: 'text-gray-500'}">{m.activityOne()}</span
			>
			<h1
				class="font-bold text-xl {activeActivity === 'one' ? 'text-primary-500' : 'text-gray-500'}"
			>
				{m.ebiosWs2_1()}
			</h1>
			<div class="flex flex-row space-x-1">
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.riskOrigin()}</span>
					<span class="font-bold">{safeTranslate(roto.risk_origin)} /</span>
				</p>
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.targetObjective()}</span>
					<span class="font-bold">{roto.target_objective}</span>
				</p>
			</div>
		</div>
		<div
			id="activityTwo"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center
                {activeActivity === 'two'
				? 'border-2 border-primary-500'
				: 'border-2 border-gray-300 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-white font-bold {activeActivity === 'two'
					? 'text-primary-500'
					: 'text-gray-500'}">{m.activityTwo()}</span
			>
			<h1
				class="font-bold text-xl {activeActivity === 'two' ? 'text-primary-500' : 'text-gray-500'}"
			>
				{m.ebiosWs2_2()}
			</h1>
			<div class="flex space-x-6">
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.motivation()}</span>
					<span class="badge text-sm font-bold">{safeTranslate(roto.motivation)}</span>
				</p>
				<i class="fa-solid fa-xmark"></i>
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.resources()}</span>
					<span class="badge text-sm font-bold">{safeTranslate(roto.resources)}</span>
				</p>
				<i class="fa-solid fa-equals"></i>
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.pertinence()}</span>
					<span class="badge text-sm font-bold {pertinenceColor[roto.pertinence]}"
						>{safeTranslate(roto.pertinence)}</span
					>
				</p>
			</div>
			<p>
				<span class="badge bg-violet-200 text-violet-700">{m.activity()}</span>
				<span>=</span>
				<span class="font-bold">{safeTranslate(roto.activity)}</span>
			</p>
		</div>
		<div
			id="activityThree"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center
                {activeActivity === 'three'
				? 'border-2 border-primary-500'
				: 'border-2 border-gray-300 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-white font-bold {activeActivity === 'three'
					? 'text-primary-500'
					: 'text-gray-500'}">{m.activityThree()}</span
			>
			<h1
				class="font-bold text-xl {activeActivity === 'three'
					? 'text-primary-500'
					: 'text-gray-500'}"
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
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-table text-gray-500 opacity-75"></i>
					<span>{m.fearedEvents()}</span>
				</h3>
				<ModelTable
					backgroundColor="bg-gray-50"
					regionBody="bg-gray-50"
					regionHeadCell="uppercase bg-gray-50 text-gray-700"
					source={data.table}
					URLModel="feared-events"
				></ModelTable>
			</div>
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-eye text-gray-500 opacity-75"></i>
					<span>{m.justification()}</span>
				</h3>
				{#if roto.justification}
					<p class="text-gray-600">{roto.justification}</p>
				{:else}
					<p class="text-gray-600">{m.noJustification()}</p>
				{/if}
			</div>
		</div>
	</div>
</div>
