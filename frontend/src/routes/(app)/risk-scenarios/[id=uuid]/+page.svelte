<script lang="ts">
	import { breadcrumbObject } from '$lib/utils/stores';
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import { URL_MODEL_MAP } from '$lib/utils/crud';

	import * as m from '$paraglide/messages';
	import { languageTag } from '$paraglide/runtime';
	import { localItems, toCamelCase } from '$lib/utils/locales';

	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';

	export let data: PageData;

	$: breadcrumbObject.set(data.scenario);

	const user = $page.data.user;
	const model = URL_MODEL_MAP['risk-scenarios'];
	const canEditObject: boolean = Object.hasOwn(user.permissions, `change_${model.name}`);

	let color_map = {};
	color_map['--'] = '#A9A9A9';
	data.riskMatrix.risk.forEach((risk, i) => {
		color_map[risk.name] = risk.hexcolor;
	});
</script>

<div class="flex flex-col space-y-3">
	<div class="flex flex-row card justify-between px-4 py-2 bg-white shadow-lg">
		<div class="flex flex-col space-y-4">
			<div>
				<p class="text-sm font-semibold text-gray-400">{m.name()}</p>
				<p class="font-semibold">{data.scenario.name}</p>
			</div>
			<div>
				<p class="text-sm font-semibold text-gray-400">{m.description()}</p>
				{#if data.scenario.description}
					<p>{data.scenario.description}</p>
				{:else}
					<p class="text-gray-400 italic text-sm">{m.noDescription()}</p>
				{/if}
			</div>
		</div>
		{#if canEditObject}
			<a
				href={`${$page.url.pathname}/edit?next=${$page.url.pathname}`}
				class="btn variant-filled-primary h-fit mt-1"
				data-testid="edit-button"><i class="fa-solid fa-pen-to-square mr-2" /> {m.edit()}</a
			>
		{/if}
	</div>

	<div class="flex flex-row space-x-2">
		<div class="card px-4 py-2 bg-white shadow-lg w-1/2">
			<h4 class="h4 font-semibold">{m.scope()}</h4>
			<div class="flex flex-row justify-between">
				<span>
					<p class="text-sm font-semibold text-gray-400">{m.project()}</p>
					<a class="anchor text-sm font-semibold" href="/projects/{data.scenario.project.id}"
						>{data.scenario.project.str}</a
					>
				</span>
				<span>
					<p class="text-sm font-semibold text-gray-400">{m.riskAssessment()}</p>
					<a
						class="anchor text-sm font-semibold"
						href="/risk-assessments/{data.scenario.risk_assessment.id}"
						>{data.scenario.risk_assessment.str}</a
					>
				</span>
				<span>
					<p class="text-sm font-semibold text-gray-400">{m.version()}</p>
					<p class="text-sm font-semibold">{data.scenario.version}</p>
				</span>
			</div>
		</div>
		<div class="card px-4 py-2 bg-white shadow-lg w-1/2">
			<h4 class="h4 font-semibold">{m.status()}</h4>
			<div class="flex flex-row justify-between">
				<div>
					<p class="text-sm font-semibold text-gray-400">{m.lastUpdate()}</p>
					<p class="text-sm font-semibold">
						{new Date(data.scenario.updated_at).toLocaleString(languageTag())}
					</p>
				</div>
				<div>
					<span class=" text-sm text-gray-400 font-semibold">Owner(s):</span>
					<ul>
						{#each data.scenario.owner as owner}
							<li class="text-xs">{owner.str}</li>
						{/each}
					</ul>
				</div>
				<div>
					<p class="text-sm font-semibold text-gray-400">{m.treatmentStatus()}</p>
					<p class="text-sm font-semibold">
						{localItems()[toCamelCase(data.scenario.treatment)]}
					</p>
				</div>
			</div>
		</div>
	</div>
	<div class="flex flex-row space-x-2">
		<div class="card px-4 py-2 bg-white shadow-lg space-y-4 w-3/5 max-h-96 overflow-y-scroll">
			<h4 class="h4 font-semibold">{m.threats()}</h4>
			<ModelTable source={data.tables['threats']} hideFilters={true} URLModel="threats" />
		</div>
		<div class="card px-4 py-2 bg-white shadow-lg w-2/5 max-h-96 overflow-y-scroll">
			<h4 class="h4 font-semibold">{m.assets()}</h4>
			<ModelTable source={data.tables['assets']} hideFilters={true} URLModel="assets" />
		</div>
	</div>
	<div class="flex flex-row space-x-4 card px-4 py-2 bg-white shadow-lg">
		<div class="flex flex-col w-1/2">
			<h4 class="h4 font-semibold">{m.currentRisk()}</h4>
			<p class="text-sm font-semibold text-gray-400">{m.existingControls()}</p>
			{#if data.scenario.existing_controls}
				<p>
					{data.scenario.existing_controls}
				</p>
			{:else}
				<p class="text-gray-400 italic text-sm">{m.noExistingControls()}</p>
			{/if}
		</div>
		<div class="flex flex-row space-x-4 my-auto items-center justify-center w-1/2 h-full">
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.probability()}</span>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20"
					style="background-color: {color_map[data.scenario.current_proba]}"
				>
					{#if localItems()[toCamelCase(data.scenario.current_proba)]}
						{localItems()[toCamelCase(data.scenario.current_proba)]}
					{:else}
						{data.scenario.current_proba}
					{/if}
				</span>
			</p>
			<i class="fa-solid fa-xmark mt-5" />
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.impact()}</span>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20"
					style="background-color: {color_map[data.scenario.current_impact]}"
				>
					{#if localItems()[toCamelCase(data.scenario.current_impact)]}
						{localItems()[toCamelCase(data.scenario.current_impact)]}
					{:else}
						{data.scenario.current_impact}
					{/if}
				</span>
			</p>
			<i class="fa-solid fa-equals mt-5" />
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.currentRiskLevel()}</span>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20"
					style="background-color: {data.scenario.current_level.hexcolor}"
				>
					{#if localItems()[toCamelCase(data.scenario.current_level.name)]}
						{localItems()[toCamelCase(data.scenario.current_level.name)]}
					{:else}
						{data.scenario.current_level.name}
					{/if}
				</span>
			</p>
		</div>
	</div>
	<div class="flex flex-row space-x-4 card px-4 py-2 bg-white shadow-lg">
		<div class="flex flex-col w-1/2">
			<h4 class="h4 font-semibold">{m.residualRisk()}</h4>
			<p class="text-sm font-semibold text-gray-400">{m.appliedControls()}</p>
			<ModelTable
				source={data.tables['applied-controls']}
				hideFilters={true}
				URLModel="applied-controls"
			/>
		</div>
		<div class="flex flex-row space-x-4 my-auto items-center justify-center w-1/2">
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.probability()}</span>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20"
					style="background-color: {color_map[data.scenario.residual_proba]}"
				>
					{#if localItems()[toCamelCase(data.scenario.residual_proba)]}
						{localItems()[toCamelCase(data.scenario.residual_proba)]}
					{:else}
						{data.scenario.residual_proba}
					{/if}
				</span>
			</p>
			<i class="fa-solid fa-xmark mt-5" />
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.impact()}</span>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20"
					style="background-color: {color_map[data.scenario.residual_impact]}"
				>
					{#if localItems()[toCamelCase(data.scenario.residual_impact)]}
						{localItems()[toCamelCase(data.scenario.residual_impact)]}
					{:else}
						{data.scenario.residual_impact}
					{/if}
				</span>
			</p>
			<i class="fa-solid fa-equals mt-5" />
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.residualRiskLevel()}</span>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20"
					style="background-color: {data.scenario.residual_level.hexcolor}"
				>
					{#if localItems()[toCamelCase(data.scenario.residual_level.name)]}
						{localItems()[toCamelCase(data.scenario.residual_level.name)]}
					{:else}
						{data.scenario.residual_level.name}
					{/if}
				</span>
			</p>
		</div>
	</div>
	<div class="card px-4 py-2 bg-white shadow-lg space-y-2">
		<div>
			<p class="text-sm font-semibold text-gray-400">{m.strengthOfKnowledge()}</p>
			<p>
				{#if data.scenario.strength_of_knowledge.symbol}
					{data.scenario.strength_of_knowledge.symbol}
				{/if}
				<span class="font-semibold">
					{#if localItems()[toCamelCase(data.scenario.strength_of_knowledge.name)]}
						{localItems()[toCamelCase(data.scenario.strength_of_knowledge.name)]}
					{:else}
						{localItems()['undefined']}
					{/if}
				</span>
			</p>
		</div>
		<div>
			<p class="text-sm font-semibold text-gray-400">{m.justification()}</p>
			<p class="">
				{#if data.scenario.justification}
					<p>{data.scenario.justification}</p>
				{:else}
					<p class="text-gray-400 italic text-sm">{m.noJustification()}</p>
				{/if}
			</p>
		</div>
	</div>
</div>
