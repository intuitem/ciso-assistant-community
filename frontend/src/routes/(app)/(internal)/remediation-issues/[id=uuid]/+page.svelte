<script lang="ts">
	import { enhance } from '$app/forms';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const issue = $derived(data.data);
	const commitment = $derived(issue.current_commitment);
	const isTerminal = $derived(issue.status === 'done' || issue.status === 'cancelled');
	const isDone = $derived(issue.status === 'done');

	let proposing = $state(false);

	const resolutionOptions = ['remediated', 'accepted_as_is', 'not_applicable'];
	const cancellationOptions = [
		'duplicate',
		'superseded',
		'withdrawn',
		'created_in_error',
		'other'
	];
	const reopenOptions = ['planned', 'in_discussion', 'in_remediation', 'in_review'];

	function acceptanceChip(state: string): string {
		if (state === 'accepted') return 'bg-success-100 text-success-700';
		if (state === 'changes_requested') return 'bg-warning-100 text-warning-700';
		return 'bg-surface-200 text-surface-700';
	}
</script>

<DetailView {data}>
	{#snippet widgets()}
		<div class="card p-4 bg-white shadow-sm space-y-4" data-testid="commitment-panel">
			<div class="text-sm text-surface-500 border-l-4 border-primary-300 pl-2">
				{m.remediationIssueNotice()}
			</div>

			<h3 class="h4 font-semibold">
				{#if commitment === null}
					{m.awaitingRemediationProposal()}
				{:else if issue.acceptance_state === 'accepted'}
					{m.agreedCommitment()}
				{:else}
					{m.proposedCommitment()}
				{/if}
			</h3>

			{#if commitment}
				<div class="space-y-2">
					<p class="whitespace-pre-wrap" data-testid="commitment-text">{commitment.text}</p>
					<p class="text-sm text-surface-500">
						v{commitment.version_number}
						{#if commitment.due_date}
							· {m.dueDate()}: {commitment.due_date}
						{/if}
					</p>
					<div class="flex flex-wrap gap-2 text-sm">
						<span class="badge {acceptanceChip(commitment.lead_acceptance)}">
							{m.lead()}: {safeTranslate(commitment.lead_acceptance)}
						</span>
						<span class="badge {acceptanceChip(commitment.respondent_acceptance)}">
							{m.respondent()}: {safeTranslate(commitment.respondent_acceptance)}
						</span>
					</div>
				</div>

				{#if !isTerminal}
					<div class="flex flex-wrap gap-2">
						<form method="POST" action="?/setAcceptance" use:enhance>
							<input type="hidden" name="state" value="accepted" />
							<button class="btn preset-filled-success-500" data-testid="accept-commitment-button">
								{m.accept()}
							</button>
						</form>
						<form method="POST" action="?/setAcceptance" use:enhance>
							<input type="hidden" name="state" value="changes_requested" />
							<button class="btn preset-tonal" data-testid="request-changes-button">
								{m.requestChanges()}
							</button>
						</form>
					</div>
				{/if}
			{/if}

			{#if !isTerminal}
				{#if proposing || commitment === null}
					<form
						method="POST"
						action="?/proposeCommitment"
						use:enhance={() =>
							async ({ update }) => {
								proposing = false;
								await update();
							}}
						class="space-y-2"
					>
						<input type="hidden" name="based_on_version_id" value={commitment?.id ?? ''} />
						<label class="label">
							<span class="text-sm font-medium">{m.commitment()}</span>
							<textarea
								class="textarea"
								name="text"
								rows="4"
								required
								data-testid="commitment-text-input"
							></textarea>
						</label>
						<label class="label">
							<span class="text-sm font-medium">{m.dueDate()}</span>
							<input class="input" type="date" name="due_date" />
						</label>
						<button class="btn preset-filled-primary-500" data-testid="propose-commitment-button">
							{m.proposeCommitment()}
						</button>
					</form>
				{:else}
					<button class="btn preset-tonal" onclick={() => (proposing = true)}>
						{m.reviseCommitment()}
					</button>
				{/if}
			{/if}

			<hr />

			<div class="flex flex-wrap gap-2">
				{#if !isTerminal}
					<form method="POST" action="?/submitReview" use:enhance>
						<button class="btn preset-tonal" data-testid="submit-review-button">
							{m.submitForReview()}
						</button>
					</form>
					<details class="w-full">
						<summary class="btn preset-filled-primary-500 cursor-pointer">
							{m.closeIssue()}
						</summary>
						<form method="POST" action="?/close" class="space-y-2 mt-2" use:enhance>
							<label class="label">
								<span class="text-sm font-medium">{m.resolution()}</span>
								<select class="select" name="resolution" required>
									{#each resolutionOptions as option}
										<option value={option}>{safeTranslate(option)}</option>
									{/each}
								</select>
							</label>
							<label class="label">
								<span class="text-sm font-medium">{m.closureJustification()}</span>
								<textarea class="textarea" name="closure_justification" rows="3" required
								></textarea>
							</label>
							<button class="btn preset-filled-primary-500" data-testid="close-issue-button">
								{m.closeIssue()}
							</button>
						</form>
					</details>
					<details class="w-full">
						<summary class="btn preset-tonal cursor-pointer">{m.cancelIssue()}</summary>
						<form method="POST" action="?/cancel" class="space-y-2 mt-2" use:enhance>
							<label class="label">
								<span class="text-sm font-medium">{m.cancellationReason()}</span>
								<select class="select" name="cancellation_reason" required>
									{#each cancellationOptions as option}
										<option value={option}>{safeTranslate(option)}</option>
									{/each}
								</select>
							</label>
							<button class="btn preset-tonal" data-testid="cancel-issue-button">
								{m.cancelIssue()}
							</button>
						</form>
					</details>
				{:else if isDone}
					<details class="w-full">
						<summary class="btn preset-tonal cursor-pointer">{m.reopen()}</summary>
						<form method="POST" action="?/reopen" class="space-y-2 mt-2" use:enhance>
							<label class="label">
								<span class="text-sm font-medium">{m.status()}</span>
								<select class="select" name="status" required>
									{#each reopenOptions as option}
										<option value={option}>{safeTranslate(option)}</option>
									{/each}
								</select>
							</label>
							<button class="btn preset-tonal" data-testid="reopen-issue-button">
								{m.reopen()}
							</button>
						</form>
					</details>
				{/if}
			</div>
		</div>
	{/snippet}
</DetailView>
