<script lang="ts">
	import { page } from '$app/state';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import type { ActionData, PageData } from './$types';

	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';

	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { isDark } from '$lib/utils/helpers';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	import { goto } from '$app/navigation';

	import { onMount } from 'svelte';
	import { canPerformAction } from '$lib/utils/access-control';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import SyncToActionsRiskModal from '$lib/components/Modals/SyncToActionsRiskModal.svelte';
	import { defaults } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import z from 'zod';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	const user = page.data.user;
	const model = URL_MODEL_MAP['risk-scenarios'];
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: model.name,
		domain: data.scenario.perimeter.folder.id
	});
	let color_map = $state({});
	color_map['--'] = '#A9A9A9';

	// Map colors for risk levels
	data.riskMatrix.risk.forEach((risk, i) => {
		color_map[risk.name] = risk.hexcolor;
	});

	// Map colors for probability levels
	data.riskMatrix.probability.forEach((prob, i) => {
		color_map[prob.name] = prob.hexcolor;
	});

	// Map colors for impact levels
	data.riskMatrix.impact.forEach((impact, i) => {
		color_map[impact.name] = impact.hexcolor;
	});

	let classesCellText = $derived((backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	});
	function handleKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return;
		// Check if the pressed key is 'e' and the edit button should be displayed

		if (event.key === 'e' && canEditObject) {
			event.preventDefault();
			goto(`${page.url.pathname}/edit?next=${page.url.pathname}`);
		}
	}

	let syncingToActionsIsLoading = $state(false);

	async function modalConfirmSyncToActions(id: string, action: string): Promise<void> {
		const appliedControlsSync = await fetch(`/risk-scenarios/${page.params.id}/sync-to-actions`, {
			method: 'POST'
		}).then((response) => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error('Failed to fetch applied controls sync data');
			}
		});
		const schema = z.object({ reset_residual: z.boolean().default(false) });
		const modalComponent: ModalComponent = {
			ref: SyncToActionsRiskModal,
			props: {
				_form: defaults({ reset_residual: false }, zod(schema)),
				schema,
				id: id,
				debug: false,
				URLModel: 'risk-scenarios',
				formAction: action,
				listProps: {
					items: appliedControlsSync.changes.map((ac) => ac.name),
					message: m.theFollowingControlsWillBeMovedToExisting()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.syncToAppliedControls(),
			body: m.syncToAppliedControlsRiskScenarioMessage({
				count: data.scenario.applied_controls.length //change this
			}),
			response: (r: boolean) => {
				syncingToActionsIsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}

	$effect(() => {
		if (syncingToActionsIsLoading === true && (form || form?.error))
			syncingToActionsIsLoading = false;
	});

	onMount(() => {
		// Add event listener when component mounts
		window.addEventListener('keydown', handleKeydown);

		// Cleanup event listener when component is destroyed
		return () => {
			window.removeEventListener('keydown', handleKeydown);
		};
	});
</script>

<div class="flex flex-col space-y-3">
	{#if data.scenario.risk_assessment?.is_locked}
		<div
			class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg shadow-sm"
		>
			<div class="flex items-center">
				<i class="fa-solid fa-lock text-yellow-600 mr-2"></i>
				<span class="font-medium">{m.lockedAssessment()}</span>
				<span class="ml-2 text-sm">{m.lockedRiskScenarioMessage()}</span>
			</div>
		</div>
	{/if}
	<div class="flex flex-row card justify-between px-4 py-2 bg-white shadow-lg">
		<div class="flex flex-col space-y-4">
			<span class="flex flex-row space-x-8">
				<div>
					<p class="text-sm font-semibold text-gray-400">{m.refId()}</p>
					<p class="font-semibold">{data.scenario.ref_id}</p>
				</div>
				<div>
					<p class="text-sm font-semibold text-gray-400">{m.name()}</p>
					<p class="font-semibold">{data.scenario.name}</p>
				</div>
			</span>
			<div>
				<p class="text-sm font-semibold text-gray-400">{m.description()}</p>
				{#if data.scenario.description}
					<p class="whitespace-pre-line">{data.scenario.description}</p>
				{:else}
					<p class="text-gray-400 italic text-sm">{m.noDescription()}</p>
				{/if}
			</div>
		</div>
		{#if canEditObject}
			<div class="flex flex-col space-y-2 my-auto">
				<Anchor
					href={`${page.url.pathname}/edit?next=${page.url.pathname}`}
					class="btn preset-filled-primary-500 h-fit mt-1"
					data-testid="edit-button"
					><i class="fa-solid fa-pen-to-square mr-2"></i> {m.edit()}</Anchor
				>
				{#if !data.scenario.risk_assessment?.is_locked}
					<button
						class="btn text-gray-100 bg-linear-to-r from-cyan-500 to-blue-500 h-fit"
						onclick={async () => {
							await modalConfirmSyncToActions(data.scenario.id, '?/syncToActions');
						}}
					>
						<span class="mr-2">
							{#if syncingToActionsIsLoading}
								<ProgressRing
									strokeWidth="16px"
									meterStroke="stroke-white"
									size="size-6"
									classes="-ml-2"
								/>
							{:else}
								<i class="fa-solid fa-arrows-rotate mr-2"></i>
							{/if}
						</span>
						{m.syncToAppliedControls()}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	<div class="flex flex-row space-x-2">
		<div class="card px-4 py-2 bg-white shadow-lg w-1/2">
			<h4 class="h4 font-semibold">{m.scope()}</h4>
			<div class="flex flex-row justify-between">
				<span>
					<p class="text-sm font-semibold text-gray-400">{m.perimeter()}</p>
					<Anchor
						class="anchor text-sm font-semibold"
						href="/perimeters/{data.scenario.perimeter.id}">{data.scenario.perimeter.str}</Anchor
					>
				</span>
				<span>
					<p class="text-sm font-semibold text-gray-400">{m.riskAssessment()}</p>
					<Anchor
						class="anchor text-sm font-semibold"
						href="/risk-assessments/{data.scenario.risk_assessment.id}"
						>{data.scenario.risk_assessment.str}</Anchor
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
						{new Date(data.scenario.updated_at).toLocaleString(getLocale())}
					</p>
				</div>
				<div>
					<span class=" text-sm text-gray-400 font-semibold">{m.owner()}</span>
					<ul>
						{#each data.scenario.owner as owner}
							<li class="text-xs font-semibold">{owner.str}</li>
						{/each}
					</ul>
				</div>
				<div>
					<p class="text-sm font-semibold text-gray-400">{m.treatmentStatus()}</p>
					<p class="text-sm font-semibold">
						{safeTranslate(data.scenario.treatment)}
					</p>
				</div>
			</div>
		</div>
	</div>
	<div class="flex flex-row space-x-2">
		<div class="card px-4 py-2 bg-white shadow-lg w-1/2 max-h-96 overflow-y-auto">
			<h4 class="h4 font-semibold">{m.assets()}</h4>
			<ModelTable
				source={data.tables['assets']}
				hideFilters={true}
				URLModel="assets"
				baseEndpoint="/assets?risk_scenarios={page.params.id}"
			/>
		</div>
		<div class="card px-4 py-2 bg-white shadow-lg space-y-4 w-1/2 max-h-96 overflow-y-auto">
			<h4 class="h4 font-semibold">{m.threats()}</h4>
			<ModelTable
				source={data.tables['threats']}
				hideFilters={true}
				URLModel="threats"
				baseEndpoint="/threats?risk_scenarios={page.params.id}"
			/>
		</div>
	</div>
	<div class="card px-4 py-2 bg-white shadow-lg max-w-full max-h-96 overflow-y-auto">
		<h4 class="h4 font-semibold">{m.vulnerabilities()}</h4>
		<ModelTable
			source={data.tables['vulnerabilities']}
			hideFilters={true}
			URLModel="vulnerabilities"
			baseEndpoint="/vulnerabilities?risk_scenarios={page.params.id}"
		/>
	</div>
	<div class="card px-4 py-2 bg-white shadow-lg max-w-full max-h-96 overflow-y-auto">
		<h4 class="h4 font-semibold">{m.securityExceptions()}</h4>
		<ModelTable
			source={data.tables['security-exceptions']}
			hideFilters={true}
			URLModel="security-exceptions"
			baseEndpoint="/security-exceptions?risk_scenarios={page.params.id}"
		/>
	</div>

	{#if page.data?.featureflags?.inherent_risk}
		<div class="flex flex-row space-x-4 card px-4 py-2 bg-white shadow-lg justify-between">
			<div class="flex flex-col w-1/2">
				<h4 class="h4 font-semibold">{m.inherentRisk()}</h4>
			</div>
			<div class="flex flex-row space-x-4 my-auto items-center justify-center w-1/2 h-full">
				<p class="flex flex-col">
					<span class="text-sm font-semibold text-gray-400">{m.probability()}</span>
					<span
						class="inline-block text-xs font-semibold text-center px-2 py-1 rounded min-w-16"
						style="background-color: {data.scenario.inherent_proba?.name
							? color_map[data.scenario.inherent_proba.name]
							: color_map['--']}"
					>
						{data.scenario.inherent_proba ? safeTranslate(data.scenario.inherent_proba.name) : '--'}
					</span>
				</p>
				<i class="fa-solid fa-xmark mt-5"></i>
				<p class="flex flex-col">
					<span class="text-sm font-semibold text-gray-400">{m.impact()}</span>
					<span
						class="inline-block text-xs font-semibold text-center px-2 py-1 rounded min-w-16"
						style="background-color: {data.scenario.inherent_impact?.name
							? color_map[data.scenario.inherent_impact.name]
							: color_map['--']}"
					>
						{data.scenario.inherent_impact
							? safeTranslate(data.scenario.inherent_impact.name)
							: '--'}
					</span>
				</p>
				<i class="fa-solid fa-equals mt-5"></i>
				<p class="flex flex-col">
					<span class="text-sm font-semibold text-gray-400 whitespace-nowrap"
						>{m.inherentRiskLevel()}</span
					>
					<span
						class="text-sm text-center font-semibold p-2 rounded-md w-20 {data.scenario
							.inherent_level
							? classesCellText(data.scenario.inherent_level.hexcolor)
							: ''}"
						style="background-color: {data.scenario.inherent_level?.hexcolor || color_map['--']}"
					>
						{data.scenario.inherent_level ? safeTranslate(data.scenario.inherent_level.name) : '--'}
					</span>
				</p>
			</div>
		</div>
	{/if}

	<div class="flex flex-row space-x-4 card px-4 py-2 bg-white shadow-lg justify-between">
		<div class="flex flex-col w-1/2">
			<h4 class="h4 font-semibold">{m.currentRisk()}</h4>
			<p class="text-sm font-semibold text-gray-400">{m.existingControls()}</p>
			<ModelTable
				source={data.tables['risk_scenarios_e']}
				hideFilters={true}
				URLModel="applied-controls"
				baseEndpoint="/applied-controls?risk_scenarios_e={page.params.id}"
			/>
		</div>
		<div class="flex flex-row space-x-4 my-auto items-center justify-center w-1/2 h-full">
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.probability()}</span>
				<span
					class="inline-block text-xs font-semibold text-center px-2 py-1 rounded min-w-16"
					style="background-color: {data.scenario.current_proba?.name
						? color_map[data.scenario.current_proba.name]
						: color_map['--']}"
				>
					{data.scenario.current_proba ? safeTranslate(data.scenario.current_proba.name) : '--'}
				</span>
			</p>
			<i class="fa-solid fa-xmark mt-5"></i>
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.impact()}</span>
				<span
					class="inline-block text-xs font-semibold text-center px-2 py-1 rounded min-w-16"
					style="background-color: {data.scenario.current_impact?.name
						? color_map[data.scenario.current_impact.name]
						: color_map['--']}"
				>
					{data.scenario.current_impact ? safeTranslate(data.scenario.current_impact.name) : '--'}
				</span>
			</p>
			<i class="fa-solid fa-equals mt-5"></i>
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400 whitespace-nowrap"
					>{m.currentRiskLevel()}</span
				>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20 {classesCellText(
						data.scenario.current_level.hexcolor
					)}"
					style="background-color: {data.scenario.current_level.hexcolor}"
				>
					{safeTranslate(data.scenario.current_level.name)}
				</span>
			</p>
		</div>
	</div>
	<div class="flex flex-row space-x-4 card px-4 py-2 bg-white shadow-lg justify-between">
		<div class="flex flex-col w-1/2">
			<h4 class="h4 font-semibold">{m.residualRisk()}</h4>
			<p class="text-sm font-semibold text-gray-400">{m.extraAppliedControls()}</p>
			<ModelTable
				source={data.tables['risk_scenarios']}
				hideFilters={true}
				URLModel="applied-controls"
				baseEndpoint="/applied-controls?risk_scenarios={page.params.id}"
			/>
		</div>
		<div class="flex flex-row space-x-4 my-auto items-center justify-center w-1/2">
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.probability()}</span>
				<span
					class="inline-block text-xs font-semibold text-center px-2 py-1 rounded min-w-16"
					style="background-color: {data.scenario.residual_proba?.name
						? color_map[data.scenario.residual_proba.name]
						: color_map['--']}"
				>
					{data.scenario.residual_proba ? safeTranslate(data.scenario.residual_proba.name) : '--'}
				</span>
			</p>
			<i class="fa-solid fa-xmark mt-5"></i>
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400">{m.impact()}</span>
				<span
					class="inline-block text-xs font-semibold text-center px-2 py-1 rounded min-w-16"
					style="background-color: {data.scenario.residual_impact?.name
						? color_map[data.scenario.residual_impact.name]
						: color_map['--']}"
				>
					{data.scenario.residual_impact ? safeTranslate(data.scenario.residual_impact.name) : '--'}
				</span>
			</p>
			<i class="fa-solid fa-equals mt-5"></i>
			<p class="flex flex-col">
				<span class="text-sm font-semibold text-gray-400 whitespace-nowrap"
					>{m.residualRiskLevel()}</span
				>
				<span
					class="text-sm text-center font-semibold p-2 rounded-md w-20 {classesCellText(
						data.scenario.residual_level.hexcolor
					)}"
					style="background-color: {data.scenario.residual_level.hexcolor}"
				>
					{safeTranslate(data.scenario.residual_level.name)}
				</span>
			</p>
		</div>
	</div>
	<div class="card px-4 py-2 bg-white shadow-lg space-y-2">
		<div>
			<p class="text-sm font-semibold text-gray-400">{m.qualifications()}</p>
			<p>
				<span class="font-semibold">
					{#each data.scenario.qualifications.sort( (a, b) => safeTranslate(a.str).localeCompare(safeTranslate(b.str)) ) as qualification, i}
						{#if i > 0},{/if}
						{safeTranslate(qualification.str) || m.undefined()}
					{/each}
				</span>
			</p>
		</div>
		<div>
			<p class="text-sm font-semibold text-gray-400">{m.strengthOfKnowledge()}</p>
			<p>
				{#if data.scenario.strength_of_knowledge.symbol}
					{data.scenario.strength_of_knowledge.symbol}
				{/if}
				<span class="font-semibold">
					{safeTranslate(data.scenario.strength_of_knowledge.name) || m.undefined()}
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
