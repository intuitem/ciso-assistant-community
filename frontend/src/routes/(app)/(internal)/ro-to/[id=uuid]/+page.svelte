<script lang="ts">
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	import { page } from '$app/stores';
	import { pageTitle } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';

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
</script>

<div class="card p-4 bg-white shadow-lg">
	<a
		href={`${$page.url.pathname}/edit?activity=${activeActivity}&next=${$page.url.pathname}?activity=${activeActivity}`}
		class="btn variant-filled-primary h-fit"
	>
		<i class="fa-solid fa-pen-to-square mr-2" data-testid="edit-button" />
		{m.edit()}
	</a>
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
			<div class="flex flex-col items-center">
				<span class="badge bg-blue-200 text-blue-700">{m.riskOrigin()}</span>
				<span class="font-bold">{roto.risk_origin}</span>
			</div>
			<div class="flex flex-col items-center">
				<span class="badge bg-cyan-200 text-cyan-700">{m.targetObjective()}</span>
				<span class="font-bold">{roto.target_objective}</span>
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
			<div class="flex space-x-6">
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.motivation()}</span>
					<span class="badge text-sm font-bold">{safeTranslate(roto.motivation)}</span>
				</p>
				<span>x</span>
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.resources()}</span>
					<span class="badge text-sm font-bold">{safeTranslate(roto.resources)}</span>
				</p>
				<span>=</span>
				<p class="flex flex-col items-center">
					<span class="text-xs text-gray-500">{m.pertinence()}</span>
					<span class="badge text-sm font-bold">{safeTranslate(roto.pertinence)}</span>
				</p>
			</div>
			<p>
				<span class="badge bg-violet-200 text-violet-700">{m.activity()}</span>
				<span>=</span>
				<span class="font-bold">{roto.activity}</span>
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
			<p>
				{#if roto.selected}
					<span class="badge bg-green-200 text-green-700">{m.selected()}</span>
				{:else}
					<span class="badge bg-red-200 text-red-700">{m.notSelected()}</span>
				{/if}
			</p>
			<!-- {#if Object.keys(data.relatedModels).length > 0}
                <div class="card shadow-lg mt-8 bg-white w-full">
                    <TabGroup justify="justify-center">
                        {#each Object.entries(data.relatedModels) as [urlmodel, model], index}
                            <Tab bind:group={tabSet} value={index} name={`${urlmodel}_tab`}>
                                {safeTranslate(model.info.localNamePlural)}
                                {#if model.table.body.length > 0}
                                    <span class="badge variant-soft-secondary">{model.table.body.length}</span>
                                {/if}
                            </Tab>
                        {/each}
                        <svelte:fragment slot="panel">
                            {#each Object.entries(data.relatedModels) as [urlmodel, model], index}
                                {#if tabSet === index}
                                    <div class="flex flex-row justify-between px-4 py-2">
                                        <h4 class="font-semibold lowercase capitalize-first my-auto">
                                            {safeTranslate('associated-' + model.info.localNamePlural)}
                                        </h4>
                                    </div>
                                    {#if model.table}
                                        <ModelTable
                                            source={model.table}
                                            deleteForm={model.deleteForm}
                                            URLModel={urlmodel}
                                        >
                                            <button
                                                slot="addButton"
                                                class="btn variant-filled-primary self-end my-auto"
                                                on:click={(_) => modalCreateForm(model)}
                                                ><i class="fa-solid fa-plus mr-2 lowercase" />{safeTranslate(
                                                    'add-' + model.info.localName
                                                )}</button
                                            >
                                        </ModelTable>
                                    {/if}
                                {/if}
                            {/each}
                        </svelte:fragment>
                    </TabGroup>
                </div>
            {/if} -->
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
