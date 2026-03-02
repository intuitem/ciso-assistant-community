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
	import {
		getModalStore,
		type ModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
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
			title: m.addEvidenceRevisionFor({ evidenceName: `${evidence.folder.str}/${evidence.str}` })
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

	async function submitDueDateChange(due_date: string): Promise<void> {
		const formData = new FormData();
		formData.append('due_date', due_date);

		const response = await fetch(`?/updateDueDate`, {
			method: 'POST',
			body: formData
		});
		if (!response.ok) {
			console.error('Failed to update due date');
		}
		invalidateAll();
	}

	async function removeEvidence(id: string, move: boolean): void {
		const formData = new FormData();
		formData.append('evidenceId', id);
		formData.append('move', move);
		const response = await fetch(`?/removeEvidence`, {
			method: 'POST',
			body: formData
		});
		if (!response.ok) {
			console.error('Failed to move legacy evidence');
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
			<Anchor
				class="text-md px-1.5 py-0.5 rounded anchor font-semibold hover:underline"
				href={`/task-templates/${taskNode.task_template.id}/`}
			>
				{taskNode.task_template.folder.str}/{taskNode.task_template.str}
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
			<input
				type="date"
				class="px-2 py-1 border rounded text-md font-semibold"
				bind:value={taskNode.due_date}
				onchange={(e) => submitDueDateChange(e.target.value)}
			/>
		</div>
	</div>

	{#if categories.some((cat) => cat.items?.length > 0)}
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
									{item.folder.str}/{item.str}
								</Anchor>
							{/each}
						</div>
					{/if}
				{/each}
			</div>
		</div>
	{/if}

	<!-- EXPECTED EVIDENCE TABLE -->
	<p class="text-gray-700 text-md font-medium mb-1">
		{m.expectedEvidence()}
		{#if taskNode.expected_evidence.length - taskNode.evidence_reviewed.length > 0}<span
				class="badge bg-amber-100 text-amber-700"
				>{taskNode.expected_evidence.length - taskNode.evidence_reviewed.length}
				{m.pending()}</span
			>{/if}
		{#if taskNode.evidence_reviewed.length > 0}<span class="badge bg-success-50 text-success-700"
				>{taskNode.evidence_reviewed.length} {m.done()}</span
			>{/if}
	</p>
	{#if taskNode.expected_evidence.length > 0}
		<table class="ml-2">
			<tbody>
				{#each taskNode.expected_evidence as evidence}
					<tr>
						<td class="py-1 pr-2 w-8 text-center">
							{#if !taskNode.evidence_reviewed.includes(evidence.id)}
								<i class="fa-solid fa-clock text-amber-700"></i>
							{:else}
								<i class="fa-solid fa-check text-success-700"></i>
							{/if}
						</td>
						<td class="py-1 font-semibold">
							<a href={`/evidences/${evidence.id}/`} class="hover:underline">
								{evidence.folder.str}/{evidence.str}
							</a>
						</td>
						<td class="py-1 pl-2 w-8 text-center">
							{#if !taskNode.evidence_reviewed.includes(evidence.id)}
								{#if page.data.user.permissions['add_evidencerevision']}
									<button
										onclick={() => modalRevisionCreate(evidence)}
										class="text-primary-500 hover:text-primary-700"
									>
										<i class="fa-solid fa-file-circle-plus"></i>
									</button>
								{/if}
							{:else}
								{@const revisionId = taskNode.evidence_revisions_map?.[evidence.id]}
								<Anchor
									href={revisionId
										? `/evidence-revisions/${revisionId}/`
										: `/evidences/${evidence.id}/`}
									label={evidence.str}
								>
									<i class="fa-solid fa-eye text-primary-500"></i>
								</Anchor>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<span class="text-md px-1.5 py-0.5 font-light italic text-gray-500">{m.noEvidences()}</span>
	{/if}

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
{#if taskNode.evidences.length > 0}
	<div class="bg-white p-4 m-4 shadow-sm rounded-lg space-y-6">
		<span class="text-gray-700 text-md font-medium mb-1">{m.legacyEvidenceField()}</span>
		<p class="text-sm font-light text-gray-500 block mb-4 whitespace-pre-line">
			{m.taskNodeLegacyEvidence()}
			<i class="fa-solid fa-square-arrow-up-right"></i>
			<i class="fa-solid fa-square-minus"></i>
		</p>
		{#each taskNode.evidences as evidence}
			<div class="flex flex-row items-center justify-start space-x-2 border-b pb-2 mb-2">
				<span class="font-semibold text-md">
					{evidence.folder.str}/{evidence.str}
				</span>
				<Anchor href={`/evidences/${evidence.id}/`} label={evidence.str}>
					<i class="fa-solid fa-eye ml-2 text-primary-500"></i>
				</Anchor>
				<button class="text-primary-500" onclick={(_) => removeEvidence(evidence.id, true)}>
					<i class="fa-solid fa-square-arrow-up-right"></i>
				</button>
				<button class="text-error-500" onclick={(_) => removeEvidence(evidence.id, false)}>
					<i class="fa-solid fa-square-minus"></i>
				</button>
			</div>
		{/each}
	</div>
{/if}
