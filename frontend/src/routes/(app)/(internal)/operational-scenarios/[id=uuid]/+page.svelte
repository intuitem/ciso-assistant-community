<script lang="ts">
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	import { page } from '$app/stores';
	import { pageTitle } from '$lib/utils/stores';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { popup, type PopupSettings } from '@skeletonlabs/skeleton';

	export let data: PageData;

	const operationalScenario = data.data;

	pageTitle.set(m.operationalScenarioRefId({ refId: operationalScenario.ref_id }));

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

	const popupLikelihood: PopupSettings = {
		event: 'click',
		target: 'popupLikelihood',
		placement: 'bottom'
	};
	const popupGravity: PopupSettings = {
		event: 'click',
		target: 'popupGravity',
		placement: 'bottom'
	};
	const popupRiskLevel: PopupSettings = {
		event: 'click',
		target: 'popupRiskLevel',
		placement: 'bottom'
	};
</script>

<div class="card p-4 bg-white shadow-lg">
	<div class="flex flex-col space-y-4 items-center">
		<h1 class="flex font-bold text-2xl space-x-2">
			<span
				><a
					class="text-primary-700 hover:text-primary-500"
					href="/ebios-rm/{operationalScenario.ebios_rm_study.id}"
					>{operationalScenario.ebios_rm_study.str}</a
				>
				- {m.operationalScenarioRefId({ refId: operationalScenario.ref_id })}</span
			>
			<p class="flex items-center">
				{#if operationalScenario.is_selected}
					<span class="badge bg-green-200 text-green-700">{m.selected()}</span>
				{:else}
					<span class="badge bg-red-200 text-red-700">{m.notSelected()}</span>
				{/if}
			</p>
		</h1>
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
				{m.ebiosWs4_1()}
			</h1>
			<a
				href={`${$page.url.pathname}/edit?activity=${activeActivity}&next=${$page.url.pathname}?activity=${activeActivity}`}
				class="btn variant-filled-primary h-fit absolute top-2 right-4"
			>
				<i class="fa-solid fa-pen-to-square mr-2" data-testid="edit-button" />
				{m.edit()}
			</a>
			{#if operationalScenario.description}
				<p class="text-gray-600">{operationalScenario.description}</p>
			{:else}
				<p class="text-gray-600">{m.noDescription()}</p>
			{/if}
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-table text-gray-500 opacity-75"></i>
					<span>{m.attackPaths()}</span>
				</h3>
				<ModelTable
					backgroundColor="bg-gray-50"
					regionBody="bg-gray-50"
					regionHeadCell="uppercase bg-gray-50 text-gray-700"
					source={data.table}
					URLModel="attack-paths"
				></ModelTable>
			</div>
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-biohazard text-red-500"></i>
					<span>{m.threats()}</span>
				</h3>
				<ul class="list-disc list-inside text-gray-600">
					{#if operationalScenario.threats?.length}
						{#each operationalScenario.threats as threat}
							<li><a class="anchor" href="/threats/{threat.id}">{threat.str}</a></li>
						{/each}
					{:else}
						<li>{m.noThreat()}</li>
					{/if}
				</ul>
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
				{m.ebiosWs4_2()}
			</h1>
			<div
				class="flex items-center w-full p-4 bg-gray-50 border rounded-md shadow-sm space-x-4 justify-between"
			>
				<div
					style="background-color: {operationalScenario.likelihood.hexcolor}"
					class="flex flex-col items-center justify-center border rounded-md p-4 font-semibold w-full"
				>
					<div
						class="card bg-black text-gray-200 p-4 z-20"
						style="color: {operationalScenario.likelihood.hexcolor}"
						data-popup={'popupLikelihood'}
					>
						<p data-testid="likelihood-description" class="font-semibold">
							{operationalScenario.likelihood.description}
						</p>
						<div class="arrow bg-black" />
					</div>
					<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
						<i class="fa-solid fa-dice text-black opacity-75"></i>
						<span>{m.likelihood()}</span>
					</h3>
					<span>{operationalScenario.likelihood.name}</span>
					<i
						class="fa-solid fa-circle-info cursor-pointer hover:opacity-70"
						use:popup={popupLikelihood}
					></i>
				</div>
				<i class="fa-solid fa-xmark"></i>
				<div
					style="background-color: {operationalScenario.gravity.hexcolor}"
					class="flex flex-col items-center justify-center border rounded-md p-4 font-semibold w-full"
				>
					<div
						class="card bg-black text-gray-200 p-4 z-20"
						style="color: {operationalScenario.gravity.hexcolor}"
						data-popup={'popupGravity'}
					>
						<p data-testid="gravity-description" class="font-semibold">
							{operationalScenario.gravity.description}
						</p>
						<div class="arrow bg-black" />
					</div>
					<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
						<i class="fa-solid fa-bomb text-black opacity-75"></i>
						<span>{m.gravity()}</span>
					</h3>
					<span>{operationalScenario.gravity.name}</span>
					<i
						class="fa-solid fa-circle-info cursor-pointer hover:opacity-70"
						use:popup={popupGravity}
					></i>
				</div>
				<i class="fa-solid fa-equals"></i>
				<div
					style="background-color: {operationalScenario.risk_level.hexcolor}"
					class="flex flex-col items-center justify-center border rounded-md p-4 font-semibold w-full"
				>
					<div
						class="card bg-black text-gray-200 p-4 z-20"
						style="color: {operationalScenario.risk_level.hexcolor}"
						data-popup={'popupRiskLevel'}
					>
						<p data-testid="risk-level-description" class="font-semibold">
							{operationalScenario.risk_level.description}
						</p>
						<div class="arrow bg-black" />
					</div>
					<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
						<i class="fa-solid fa-circle-radiation text-black opacity-75"></i>
						<span>{m.riskLevel()}</span>
					</h3>
					<span>{operationalScenario.risk_level.name}</span>
					<i
						class="fa-solid fa-circle-info cursor-pointer hover:opacity-70"
						use:popup={popupRiskLevel}
					></i>
				</div>
			</div>
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-eye text-gray-500 opacity-75"></i>
					<span>{m.justification()}</span>
				</h3>
				{#if operationalScenario.justification}
					<p class="text-gray-600">{operationalScenario.justification}</p>
				{:else}
					<p class="text-gray-600">{m.noJustification()}</p>
				{/if}
			</div>
		</div>
	</div>
</div>
