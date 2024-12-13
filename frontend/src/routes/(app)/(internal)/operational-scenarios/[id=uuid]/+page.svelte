<script lang="ts">
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	import { page } from '$app/stores';
	import { pageTitle } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';

	export let data: PageData;

	const operationalScenario = data.data;

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

	const likelihoodChoices = [
		{ label: m.unlikely(), value: 0 },
		{ label: m.likely(), value: 1 },
		{ label: m.veryLikely(), value: 2 },
		{ label: m.certain(), value: 3 }
	];
	const gravityChoices = [
		{ label: m.minor(), value: 0 },
		{ label: m.significant(), value: 1 },
		{ label: m.important(), value: 2 },
		{ label: m.critical(), value: 3 }
	];
</script>

<div class="card p-4 bg-white shadow-lg">
	<div class="flex flex-col space-y-4">
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
			<p>
				{#if operationalScenario.is_selected}
					<span class="badge bg-green-200 text-green-700">{m.selected()}</span>
				{:else}
					<span class="badge bg-red-200 text-red-700">{m.notSelected()}</span>
				{/if}
			</p>
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-dice text-black opacity-75"></i>
					<span>{m.likelihood()}</span>
				</h3>
				<div class="grid grid-cols-4 gap-2 p-2">
					{#each likelihoodChoices as choice}
						{#if operationalScenario.likelihood.value === choice.value}
							<div
								style="background-color: {operationalScenario.likelihood.hexcolor}"
								class="flex flex-col items-center justify-center border rounded-md p-4 font-semibold"
							>
								<span>{choice.label}</span>
								<span>({choice.value})</span>
							</div>
						{:else}
							<div
								class="flex flex-col items-center justify-center border rounded-md bg-gray-200 p-4 text-gray-500"
							>
								<span>{choice.label}</span>
								<span>({choice.value})</span>
							</div>
						{/if}
					{/each}
				</div>
			</div>
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-bomb text-black opacity-75"></i>
					<span>{m.gravity()}</span>
				</h3>
				<div class="grid grid-cols-4 gap-2 p-2">
					{#each gravityChoices as choice}
						{#if operationalScenario.gravity.value === choice.value}
							<div
								style="background-color: {operationalScenario.gravity.hexcolor}"
								class="flex flex-col items-center justify-center border rounded-md p-4 font-semibold"
							>
								<span>{choice.label}</span>
								<span>({choice.value})</span>
							</div>
						{:else}
							<div
								class="flex flex-col items-center justify-center border rounded-md bg-gray-200 p-4 text-gray-500"
							>
								<span>{choice.label}</span>
								<span>({choice.value})</span>
							</div>
						{/if}
					{/each}
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
