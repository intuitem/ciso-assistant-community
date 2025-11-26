<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import { m, noEvidences } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import TableMarkdownField from '$lib/components/Forms/TableMarkdownField.svelte';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	console.log('data in task node detail page:', data);

	const taskNode = data.data;
</script>

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
				{#each taskNode.expected_evidence as evidence}
					<div
						class="p-2 bg-red-50 border border-red-200 rounded min-h-[40px] flex flex-col items-center justify-center hover:bg-red-100 transition cursor-pointer"
					>
						<span class="text-red-700">{evidence.str}</span>
						<span class="font-light text-gray-400 italic text-sm">{m.toDo()}</span>
						<i class="fa-solid fa-file-circle-plus text-red-700"></i>
					</div>
				{/each}
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
