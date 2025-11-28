<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import TableMarkdownField from '$lib/components/Forms/TableMarkdownField.svelte';
	import { superValidate } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { modelSchema } from '$lib/utils/schemas';
	import { getModelInfo } from '$lib/utils/crud';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { page } from '$app/state';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	async function modalRevisionCreate(evidence): void {
		const model = getModelInfo('evidence-revisions');
		const createSchema = modelSchema(model.urlModel);
		const initialData = {
			evidence: evidence.id,
			folder: evidence.folder.id,
			task_node: data.data.id
		};
		const createForm = await superValidate(initialData, zod(createSchema), { errors: false });
		let modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createForm,
				model: model,
				debug: false,
				customNameDescription: false,
				formAction: `?/addEvidenceRevision`
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.addEvidenceRevisionFor({evidenceName: `${evidence.folder.str}/${evidence.str}`})
		};
		modalStore.trigger(modal);
	}

	let taskNode = $derived(data.data);

	async function submitStatusChange(status: string): void {
		const formData = new FormData();
		formData.append('status', status);

		const response = await fetch(`?/${status}`, {
			method: 'POST',
			body: formData
		});
		if (!response.ok) {
			console.error('Failed to update status');
			return;
		}
		invalidateAll();
	}

	async function submitObservationChange(observation: string): void {
		const formData = new FormData();
		formData.append('observation', observation);

		const response = await fetch(`?/updateObservation`, {
			method: 'POST',
			body: formData
		});
		if (!response.ok) {
			console.error('Failed to update observation');
			return;
		}
		invalidateAll();
	}

	const categories = [
		{
			label: m.appliedControls(),
			items: taskNode.applied_controls,
			baseUrl: '/applied-controls'
		},
		{
			label: m.complianceAssessments(),
			items: taskNode.compliance_assessments,
			baseUrl: '/compliance-assessments'
		},
		{
			label: m.assets(),
			items: taskNode.assets,
			baseUrl: '/assets'
		},
		{
			label: m.riskAssessments(),
			items: taskNode.risk_assessments,
			baseUrl: '/risk-assessments'
		},
		{
			label: m.findingsAssessments(),
			items: taskNode.findings_assessment,
			baseUrl: '/finding-assessments'
		}
	];
</script>

<div class="bg-white p-4 m-4 shadow-sm rounded-lg space-y-6">
	<!-- HEADER COMPACT -->
	<div class="flex flex-row justify-between">
		<!-- Task -->
		<div class="space-y-1">
			<p class="text-gray-700 text-md font-medium tracking-wide">
				{m.taskTemplate()}
			</p>
			<Anchor class="text-md px-1.5 py-0.5 rounded anchor font-semibold hover:underline">
				{taskNode.task_template.str}
			</Anchor>
		</div>

		<!-- Assigned to -->
		<div class="space-y-1">
			<p class="text-gray-700 text-md font-medium tracking-wide">
				{m.assignedTo()}
			</p>
			<div class="flex flex-col">
				{#each taskNode.assigned_to as user}
					<Anchor class="text-md px-1.5 py-0.5 rounded anchor font-semibold hover:underline">
						{user.str}
					</Anchor>
				{:else}
					<p class="text-md px-1.5 py-0.5 font-light italic text-gray-500">{m.unassigned()}</p>
				{/each}
			</div>
		</div>

		<!-- Due date -->
		<div class="space-y-1">
			<p class="text-gray-700 text-md font-medium tracking-wide">
				{m.occurrenceDueDate()}
			</p>
			<p class="text-md px-1.5 py-0.5 font-semibold">
				{taskNode.due_date}
			</p>
		</div>
	</div>

	<div>
		<p class="text-gray-700 text-md font-medium mb-2">
			{m.relatedTo()}
		</p>
		<div class="grid grid-cols-2 gap-6 border rounded-lg p-4 bg-gray-50 place-items-center">
			{#each categories as cat}
				{#if cat.items?.length}
					<div class="flex flex-col space-y-1">
						<p class="text-gray-700 text-md font-medium tracking-wide">
							{cat.label}
						</p>

						{#each cat.items as item}
							<Anchor
								class="text-md px-1.5 py-0.5 anchor font-semibold"
								href="{cat.baseUrl}/{item.id}"
							>
								{item.str}
							</Anchor>
						{/each}
					</div>
				{/if}
			{/each}
		</div>
	</div>

	<!-- GRID VERY COMPACT -->
	 <p class="text-gray-700 text-md font-medium mb-1">
		{m.expectedEvidence()}
		{#if taskNode.expected_evidence.length - taskNode.evidence_reviewed.length > 0}<span
				class="badge bg-amber-100 text-amber-700"
				>{taskNode.expected_evidence.length - taskNode.evidence_reviewed.length}
				{m.pending()}</span
			>{/if}
		{#if taskNode.evidence_reviewed.length > 0}<span
				class="badge bg-success-50 text-success-700"
				>{taskNode.evidence_reviewed.length} {m.done()}</span
			>{/if}
	</p>
	<div class="grid grid-cols-3 gap-3">
		{#if taskNode.expected_evidence.length > 0}
			<div class="flex flex-col p-2 space-y-2">
				{#each taskNode.expected_evidence as evidence}
					{#if !taskNode.evidence_reviewed.includes(evidence.id)}
						{#if page.data.user.permissions['add_evidencerevision']}
							<div class="flex flex-row items-center">
								<i class="fa-solid fa-clock mr-2 text-amber-700"></i>
								<span class="font-semibold">{evidence.str}</span>
								<button
									class="flex flex-row items-center"
									onclick={() => modalRevisionCreate(evidence)}
								>
									<i class="fa-solid fa-file-circle-plus ml-2 text-primary-500"></i>
								</button>
							</div>
						{:else}
							<Anchor href={`/evidences/${evidence.id}/`} class="flex flex-row items-center">
								<i class="fa-solid fa-clock mr-2 text-amber-700"></i>
								<span class="font-semibold">{evidence.str}</span>
							</Anchor>
						{/if}
					{:else}
						<div class="flex flex-row items-center">
							<i class="fa-solid fa-check mr-2 text-success-700"></i>
							<span class="font-semibold">{evidence.str}</span>
							<Anchor href={`/evidences/${evidence.id}/`} label={evidence.str}>
								<i class="fa-solid fa-eye ml-2 text-primary-500"></i>
							</Anchor>
						</div>
					{/if}
				{/each}
			</div>
		{:else}
			<span class="text-md px-1.5 py-0.5 font-light italic text-gray-500">{m.noEvidences()}</span>
		{/if}
	</div>

	<!-- OBSERVATION COMPACT -->
	<div class="space-y-1">
		<p class="text-gray-700 text-md font-medium">{m.observation()}</p>
		<div class="p-2 bg-gray-50 border border-gray-200 rounded">
			<TableMarkdownField
				bind:value={taskNode.observation}
				onSave={async (observation) => {
					submitObservationChange(observation);
				}}
			/>
		</div>
	</div>

	<!-- Status (compact buttons) -->
	<div class="flex space-y-1 flex-col justify-self-end">
		<p class="text-gray-700 text-md font-medium">{m.status()}</p>
		{#key taskNode}
			<div class="flex flex-wrap gap-1">
				<button
					onclick={() => {
						submitStatusChange('pending');
					}}
					class="px-4 py-0.5 rounded-lg text-md border
			{taskNode.status === 'pending'
						? 'bg-amber-500 text-white border-amber-600'
						: 'bg-white border-gray-300 text-gray-700 hover:bg-amber-50'}"
				>
					{m.pending()}
				</button>

				<button
					onclick={() => {
						submitStatusChange('inProgress');
					}}
					class="px-4 py-0.5 rounded-lg text-md border
			{taskNode.status === 'in_progress'
						? 'bg-blue-500 text-white border-blue-600'
						: 'bg-white border-gray-300 text-gray-700 hover:bg-blue-50'}"
				>
					{m.inProgress()}
				</button>

				<button
					onclick={() => {
						submitStatusChange('cancelled');
					}}
					class="px-4 py-0.5 rounded-lg text-md border
			{taskNode.status === 'cancelled'
						? 'bg-error-500 text-white border-error-600'
						: 'bg-white border-gray-300 text-gray-700 hover:bg-error-50'}"
				>
					{m.cancelled()}
				</button>

				<button
					onclick={() => {
						submitStatusChange('completed');
					}}
					class="px-4 py-0.5 rounded-lg text-md border
			{taskNode.status === 'completed'
						? 'bg-success-500 text-white border-success-600'
						: 'bg-white border-gray-300 text-gray-700 hover:bg-success-50'}"
				>
					{m.completed()}
				</button>
			</div>
		{/key}
	</div>
</div>
<div class="bg-white p-4 m-4 shadow-sm rounded-lg space-y-6">
	<span class="text-gray-700 text-md font-medium mb-1">{m.legacyEvidenceField()}</span>
	<p class="text-sm font-light text-gray-500 block mb-4 whitespace-pre-line">
		{m.taskNodeLegacyEvidence()}
	</p>
	{#each taskNode.evidences as evidence}
		<div class="flex flex-row items-center justify-between border-b pb-2 mb-2">
			<Anchor href={`/evidences/${evidence.id}/`} class="font-semibold text-md anchor">
				{evidence.str}
			</Anchor>
		</div>
	{/each}
</div>
