<script lang="ts">
	import { page } from '$app/state';
	import { goto, refreshAll } from '$app/navigation';
	import { deserialize } from '$app/forms';
	import { m } from '#paraglide/messages.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { isOpenTask } from '#lib/utils/vendorTasks.js';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import CommitmentPanel from '#lib/components/CommitmentPanel/CommitmentPanel.svelte';

	let { data: incoming } = $props();
	// SvelteKit hands the next page's data to this page before unmounting it.
	let lastData = incoming;
	const data = $derived.by(() => (incoming.tasks ? (lastData = incoming) : lastData));

	const toastStore = getToastStore();
	let expandedTask = $state<string | null>(null);
	const showCommitment = $derived(!!page.data?.featureflags?.commitment_management);
	const due = (task: Record<string, any>) => task.task_date ?? task.next_occurrence;
	const tasks = $derived(
		[...data.tasks].sort(
			(a: Record<string, any>, b: Record<string, any>) =>
				Number(isOpenTask(b)) - Number(isOpenTask(a)) ||
				(due(a) ?? '9999').localeCompare(due(b) ?? '9999')
		)
	);

	const links = (task: Record<string, any>) =>
		[...task.requirement_assessments, ...task.compliance_assessments]
			.map((o: { id: string }) => data.links[o.id])
			.filter(Boolean);

	const taskHref = (task: Record<string, any>) => {
		const ra = task.requirement_assessments.find((o: { id: string }) => data.links[o.id]);
		return ra ? `${data.links[ra.id].href}&task=${task.id}` : null;
	};

	async function updateStatus(id: string, status: string) {
		const res = await fetch('?/updateStatus', {
			method: 'POST',
			body: JSON.stringify({ id, status })
		});
		const result = deserialize(await res.text());
		if (result.type !== 'success' || (result.data?.status as number) >= 400) {
			toastStore.trigger({ message: m.anErrorOccurred(), background: 'preset-filled-error-500' });
		}
		await refreshAll();
	}
</script>

<div class="card bg-white dark:bg-surface-900 p-4 shadow-sm">
	<label class="flex items-center gap-2 pb-4 text-sm">
		<input
			type="checkbox"
			class="checkbox"
			checked={data.mine}
			onchange={() => goto(data.mine ? '/my-tasks' : '/my-tasks?mine')}
			data-testid="assigned-to-me"
		/>
		{m.assignedToMe()}
	</label>
	{#if !tasks.length}
		<p class="text-sm text-surface-600-400">{m.noTaskTemplates()}</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="w-full text-sm" data-testid="my-tasks-table">
				<thead class="text-surface-600-400 border-b border-surface-200-800">
					<tr>
						<th class="text-left font-medium py-2">{m.name()}</th>
						<th class="text-left font-medium py-2">{m.questionnaire()}</th>
						<th class="text-left font-medium py-2">{m.dueDate()}</th>
						<th class="text-left font-medium py-2">{m.status()}</th>
						{#if showCommitment}
							<th class="text-left font-medium py-2">{m.commitment()}</th>
							<th class="w-8"></th>
						{/if}
					</tr>
				</thead>
				<tbody>
					{#each tasks as task (task.id)}
						{@const href = taskHref(task)}
						<tr class="border-b border-surface-100-900" class:opacity-60={!isOpenTask(task)}>
							<td class="py-2">
								{#if href}
									<a {href} class="font-medium text-primary-500 hover:underline">{task.name}</a>
								{:else}
									{task.name}
								{/if}
							</td>
							<td class="py-2 text-surface-600-400">
								{#each links(task) as link}
									<a href={link.href} class="block hover:underline">{link.label}</a>
								{:else}
									--
								{/each}
							</td>
							<td class="py-2">{due(task) ?? '--'}</td>
							<td class="py-2">
								{#if task.status}
									<select
										class="select select-sm text-xs w-36"
										aria-label={m.status()}
										value={task.status}
										onchange={(e) => updateStatus(task.id, e.currentTarget.value)}
										data-testid="task-status"
									>
										{#each Object.keys(data.statusOptions) as value}
											<option {value}>{safeTranslate(value)}</option>
										{/each}
									</select>
								{:else}
									{task.next_occurrence_status ? safeTranslate(task.next_occurrence_status) : '--'}
								{/if}
							</td>
							{#if showCommitment}
								<td class="py-2">
									{task.commitment_state && task.commitment_state !== '--'
										? safeTranslate(task.commitment_state)
										: '--'}
									{#if task.committed_eta}
										<span class="text-xs text-surface-600-400">({task.committed_eta})</span>
									{/if}
								</td>
								<td class="py-2 text-right">
									<button
										type="button"
										class="btn-icon btn-icon-sm preset-tonal-surface"
										aria-label={m.commitment()}
										aria-expanded={expandedTask === task.id}
										onclick={() => (expandedTask = expandedTask === task.id ? null : task.id)}
										data-testid="task-commitment-toggle"
									>
										<i
											class="fa-solid {expandedTask === task.id
												? 'fa-chevron-up'
												: 'fa-chevron-down'}"
										></i>
									</button>
								</td>
							{/if}
						</tr>
						{#if showCommitment && expandedTask === task.id}
							<tr>
								<td colspan="6" class="pb-3">
									<CommitmentPanel urlModel="task-templates" object={task} />
								</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
