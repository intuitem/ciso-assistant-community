<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import TableMarkdownField from '$lib/components/Forms/TableMarkdownField.svelte';
	import { superValidate } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { type AnyZodObject } from 'zod';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { modelSchema } from '$lib/utils/schemas';
	import { getModelInfo } from '$lib/utils/crud';
	import { getModalStore } from '$lib/components/Modals/stores';
	import { page } from '$app/state';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	console.log('data in task node detail page:', data);

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
				formAction: `?/create`
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.addEvidenceRevision()
		};
		modalStore.trigger(modal);
	}

	const taskNode = data.data;

	let revisions_task_node_id = $state(new Set<string>());

	for (let rev of data.data.evidence_revisions) {
		revisions_task_node_id.add(rev.task_node);
	}

	$inspect(data)
</script>

{#key data.data}
<div class="bg-white p-4 m-4 shadow-sm rounded-lg space-y-6">
	<!-- HEADER COMPACT -->
	<div class="grid grid-cols-3 gap-4 items-center">
		<!-- Assigned to -->
		<div class="space-y-1">
			<p class="text-gray-700 text-md font-medium tracking-wide">
				{m.assignedTo()}
			</p>
			<div class="flex flex-wrap gap-1">
				{#each taskNode.assigned_to as user}
					<Anchor class="text-md bg-gray-100 hover:bg-gray-200 px-1.5 py-0.5 rounded anchor">
						{user.str}
					</Anchor>
				{/each}
			</div>
		</div>

		<!-- Due date -->
		<div class="space-y-1">
			<p class="text-gray-700 text-md font-medium tracking-wide">
				{m.dueDate()}
			</p>
			<p class="font-semibold text-sm">
				{taskNode.due_date}
			</p>
		</div>

		<!-- Status (compact buttons) -->
		<div class="flex flex-wrap gap-1 justify-end">
			<button
				class="px-4 py-0.5 rounded text-md border
                {taskNode.status === 'pending'
					? 'bg-blue-500 text-white border-blue-600'
					: 'bg-white border-gray-300 text-gray-700 hover:bg-blue-50'}"
			>
				{m.pending()}
			</button>

			<button
				class="px-4 py-0.5 rounded text-md border
                {taskNode.status === 'in_progress'
					? 'bg-yellow-500 text-white border-yellow-600'
					: 'bg-white border-gray-300 text-gray-700 hover:bg-yellow-50'}"
			>
				{m.inProgress()}
			</button>

			<button
				class="px-4 py-0.5 rounded text-md border
                {taskNode.status === 'cancelled'
					? 'bg-red-500 text-white border-red-600'
					: 'bg-white border-gray-300 text-gray-700 hover:bg-red-50'}"
			>
				{m.cancelled()}
			</button>

			<button
				class="px-4 py-0.5 rounded text-md border
                {taskNode.status === 'completed'
					? 'bg-green-500 text-white border-green-600'
					: 'bg-white border-gray-300 text-gray-700 hover:bg-green-50'}"
			>
				{m.completed()}
			</button>
		</div>
	</div>

	<!-- GRID VERY COMPACT -->
	<div class="grid grid-cols-3 gap-3">
		{#if taskNode.expected_evidence.length > 0}
			<div>
				<p class="text-gray-700 text-md font-medium mb-1">
					{m.expectedEvidence()}<span class="badge bg-primary-50 ml-1"
						>{taskNode.expected_evidence.length}</span
					>
				</p>
				{#key data}
					{#each taskNode.expected_evidence as evidence}
						{#key data}
							{#if revisions_task_node_id.has(taskNode.id)}
								<Anchor
									href={`/evidences/${evidence.id}/`}
									class="p-2 px-10 bg-green-50 border border-green-200 rounded flex flex-col items-center justify-center hover:bg-green-100 transition"
								>
									<span class="text-green-700">{evidence.str}</span>
									<span class="font-light text-gray-400 italic text-sm">{m.done()}</span>
									<i class="fa-solid fa-circle-check text-green-700 ml-2"></i>
								</Anchor>
							{:else}
								{#if page.data.user.permissions['add_evidencerevision']}
									<button
										class="p-2 px-10 bg-red-50 border border-red-200 rounded flex flex-col items-center justify-center hover:bg-red-100 transition"
										onclick={() => modalRevisionCreate(evidence)}
									>
										<span class="text-red-700">{evidence.str}</span>
										<span class="font-light text-gray-400 italic text-sm">{m.toDo()}</span>
										<i class="fa-solid fa-file-circle-plus text-red-700"></i>
									</button>
								{:else}
									<Anchor
										href={`/evidences/${evidence.id}/`}
										class="p-2 px-10 bg-red-50 border border-red-200 rounded flex flex-col items-center justify-center hover:bg-red-100 transition"
									>
										<span class="text-red-700">{evidence.str}</span>
										<span class="font-light text-gray-400 italic text-sm">{m.toDo()}</span>
										<i class="fa-solid fa-circle-minus text-red-700 ml-2"></i>
									</Anchor>
								{/if}
							{/if}
						{/key}
					{/each}
				{/key}
			</div>
		{:else}
			<span>{m.noEvidences()}</span>
		{/if}
	</div>

	<!-- OBSERVATION COMPACT -->
	<div class="space-y-1">
		<p class="text-gray-700 text-md font-medium">{m.observation()}</p>
		<div class="p-2 bg-gray-50 border border-gray-200 rounded">
			<TableMarkdownField bind:value={taskNode.observation} />
		</div>
	</div>
</div>
{/key}