<script lang="ts">
	import { page } from '$app/state';
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { canPerformAction } from '$lib/utils/access-control';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const user = page.data.user;
	const validation_flow = data.validation_flow;

	const canEdit: boolean = canPerformAction({
		user,
		action: 'change',
		model: 'validationflow',
		domain: validation_flow.folder.id
	});

	// Check if current user is the approver or requester (compare as strings to handle type differences)
	const isApprover = String(user.id) === String(validation_flow.approver?.id);
	const isRequester = String(user.id) === String(validation_flow.requester?.id);

	// Modal state
	let showObservationModal = $state(false);
	let currentAction = $state<
		'approve' | 'reject' | 'revoke' | 'drop' | 'request_changes' | 'resubmit' | null
	>(null);
	let notes = $state('');
	let isSubmitting = $state(false);

	function openObservationModal(
		action: 'approve' | 'reject' | 'revoke' | 'drop' | 'request_changes' | 'resubmit'
	) {
		console.log('Opening modal for action:', action);
		currentAction = action;
		notes = ''; // Reset notes for new action
		showObservationModal = true;
		console.log('Modal state:', { currentAction, showObservationModal });
	}

	function closeObservationModal() {
		showObservationModal = false;
		currentAction = null;
	}

	async function handleConfirmAction() {
		if (!currentAction || isSubmitting) return;
		isSubmitting = true;

		console.log('Submitting action:', currentAction, 'with notes:', notes);

		const formData = new FormData();
		formData.append('notes', notes);

		try {
			const response = await fetch(`?/${currentAction}`, {
				method: 'POST',
				body: formData
			});

			console.log('Response status:', response.status, response.ok);

			if (response.ok) {
				console.log('Action successful, closing modal and refreshing...');
				closeObservationModal();
				// Force a full page reload to update the status and hide buttons
				window.location.reload();
			} else {
				const errorData = await response.text();
				console.error('Action failed:', response.status, errorData);
				alert(`Error: ${response.status} - ${errorData}`);
			}
		} catch (error) {
			console.error('Error submitting action:', error);
			alert('An error occurred while submitting the action.');
		} finally {
			isSubmitting = false;
		}
	}

	// Helper to convert model field names to display names
	const modelDisplayNames: Record<string, string> = {
		compliance_assessments: m.complianceAssessments(),
		risk_assessments: m.riskAssessments(),
		business_impact_analysis: m.businessImpactAnalysis(),
		crq_studies: m.quantitativeRiskStudies(),
		ebios_studies: m.ebiosRMStudies(),
		entity_assessments: m.entityAssessments(),
		findings_assessments: m.findingsAssessments(),
		evidences: m.evidences(),
		security_exceptions: m.securityExceptions(),
		policies: m.policies()
	};

	// Get URL model names for links
	const modelUrlNames: Record<string, string> = {
		compliance_assessments: 'compliance-assessments',
		risk_assessments: 'risk-assessments',
		business_impact_analysis: 'business-impact-analysis',
		crq_studies: 'quantitative-risk-studies',
		ebios_studies: 'ebios-rm',
		entity_assessments: 'entity-assessments',
		findings_assessments: 'findings-assessments',
		evidences: 'evidences',
		security_exceptions: 'security-exceptions',
		policies: 'policies'
	};

	// Get status color
	const statusColors: Record<string, string> = {
		submitted: 'bg-blue-100 text-blue-800',
		accepted: 'bg-green-100 text-green-800',
		rejected: 'bg-red-100 text-red-800',
		revoked: 'bg-gray-100 text-gray-800',
		expired: 'bg-orange-100 text-orange-800',
		dropped: 'bg-gray-100 text-gray-800',
		change_requested: 'bg-yellow-100 text-yellow-800'
	};
</script>

<div class="flex flex-col space-y-4">
	<div class="card px-6 py-4 bg-white shadow-lg">
		<div class="flex justify-between items-start mb-4">
			<div class="flex flex-col space-y-2">
				<h1 class="text-2xl font-bold">{validation_flow.str}</h1>
				<span
					class="badge {statusColors[validation_flow.status] ||
						'bg-gray-100 text-gray-800'} px-3 py-1 rounded-full text-sm font-medium w-fit"
				>
					{safeTranslate(validation_flow.status)}
				</span>
			</div>
			<div class="flex flex-col space-y-2">
				{#if validation_flow.status === 'submitted' && isApprover}
					<!-- Approver actions for submitted status -->
					<div class="flex flex-wrap gap-2">
						<button
							type="button"
							onclick={() => openObservationModal('approve')}
							class="btn preset-filled-success-500"
							data-testid="approve-button"
						>
							<i class="fa-solid fa-check mr-2"></i>
							{m.approve()}
						</button>
						<button
							type="button"
							onclick={() => openObservationModal('reject')}
							class="btn preset-filled-error-500"
							data-testid="reject-button"
						>
							<i class="fa-solid fa-times mr-2"></i>
							{m.reject()}
						</button>
						<button
							type="button"
							onclick={() => openObservationModal('request_changes')}
							class="btn preset-filled-warning-500"
							data-testid="request-changes-button"
						>
							<i class="fa-solid fa-pencil mr-2"></i>
							{m.requestChanges()}
						</button>
						<button
							type="button"
							onclick={() => openObservationModal('drop')}
							class="btn preset-filled-surface-500"
							data-testid="drop-button"
						>
							<i class="fa-solid fa-trash mr-2"></i>
							{m.drop()}
						</button>
					</div>
				{:else if validation_flow.status === 'accepted' && isApprover}
					<!-- Approver actions for accepted status -->
					<button
						type="button"
						onclick={() => openObservationModal('revoke')}
						class="btn preset-filled-warning-500"
						data-testid="revoke-button"
					>
						<i class="fa-solid fa-ban mr-2"></i>
						{m.revoke()}
					</button>
				{:else if validation_flow.status === 'change_requested' && isRequester}
					<!-- Requester actions for change_requested status -->
					<div class="flex flex-wrap gap-2">
						<button
							type="button"
							onclick={() => openObservationModal('resubmit')}
							class="btn preset-filled-primary-500"
							data-testid="resubmit-button"
						>
							<i class="fa-solid fa-paper-plane mr-2"></i>
							{m.resubmit()}
						</button>
						<button
							type="button"
							onclick={() => openObservationModal('drop')}
							class="btn preset-filled-surface-500"
							data-testid="drop-button"
						>
							<i class="fa-solid fa-trash mr-2"></i>
							{m.drop()}
						</button>
					</div>
				{:else if ['rejected', 'revoked', 'expired', 'dropped'].includes(validation_flow.status)}
					<!-- Terminal states - no actions available -->
					<div class="text-sm text-gray-500 italic">
						{m.noActionsAvailableForThisStatus()}
					</div>
				{:else if validation_flow.status === 'submitted'}
					<!-- Not the approver for submitted status -->
					<div
						class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg text-sm"
					>
						<i class="fa-solid fa-exclamation-triangle mr-2"></i>
						{m.onlyApproverCanModify()}
					</div>
				{:else if validation_flow.status === 'change_requested'}
					<!-- Not the requester for change_requested status -->
					<div
						class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg text-sm"
					>
						<i class="fa-solid fa-exclamation-triangle mr-2"></i>
						{m.onlyRequesterCanModify()}
					</div>
				{/if}
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<div class="space-y-2">
				<div class="text-sm font-medium text-gray-700">{m.domain()}</div>
				<div class="text-sm text-gray-600">
					<Anchor href="/folders/{validation_flow.folder.id}" class="anchor">
						{validation_flow.folder.str}
					</Anchor>
				</div>
			</div>

			{#if validation_flow.filtering_labels && validation_flow.filtering_labels.length > 0}
				<div class="space-y-2">
					<div class="text-sm font-medium text-gray-700">{m.filteringLabels()}</div>
					<div class="flex flex-wrap gap-2">
						{#each validation_flow.filtering_labels as label}
							<Anchor href="/filtering-labels/{label.id}" class="anchor">
								<span class="badge preset-tonal-primary px-2 py-1 rounded text-xs">
									{label.str}
								</span>
							</Anchor>
						{/each}
					</div>
				</div>
			{/if}

			<div class="space-y-2">
				<div class="text-sm font-medium text-gray-700">{m.requester()}</div>
				<div class="text-sm text-gray-600">
					{#if validation_flow.requester}
						{#if validation_flow.requester.first_name || validation_flow.requester.last_name}
							{validation_flow.requester.first_name}
							{validation_flow.requester.last_name}
							<span class="text-gray-500">({validation_flow.requester.email})</span>
						{:else}
							{validation_flow.requester.email}
						{/if}
					{:else}
						--
					{/if}
				</div>
			</div>

			<div class="space-y-2">
				<div class="text-sm font-medium text-gray-700">{m.approver()}</div>
				<div class="text-sm text-gray-600">
					{#if validation_flow.approver}
						{#if validation_flow.approver.first_name || validation_flow.approver.last_name}
							{validation_flow.approver.first_name}
							{validation_flow.approver.last_name}
							<span class="text-gray-500">({validation_flow.approver.email})</span>
						{:else}
							{validation_flow.approver.email}
						{/if}
					{:else}
						--
					{/if}
				</div>
			</div>

			{#if validation_flow.validation_deadline}
				<div class="space-y-2">
					<div class="text-sm font-medium text-gray-700">{m.validationDeadline()}</div>
					<div class="text-sm text-gray-600">
						{formatDateOrDateTime(validation_flow.validation_deadline, getLocale())}
					</div>
				</div>
			{/if}

			<div class="space-y-2">
				<div class="text-sm font-medium text-gray-700">{m.createdAt()}</div>
				<div class="text-sm text-gray-600">
					{formatDateOrDateTime(validation_flow.created_at, getLocale())}
				</div>
			</div>

			<div class="space-y-2">
				<div class="text-sm font-medium text-gray-700">{m.updatedAt()}</div>
				<div class="text-sm text-gray-600">
					{formatDateOrDateTime(validation_flow.updated_at, getLocale())}
				</div>
			</div>
		</div>

		{#if validation_flow.request_notes}
			<div class="mt-4 space-y-2">
				<div class="text-sm font-medium text-gray-700">{m.requestNotes()}</div>
				<div class="p-3 bg-gray-50 rounded-lg text-sm">
					<MarkdownRenderer content={validation_flow.request_notes} />
				</div>
			</div>
		{/if}
	</div>

	<!-- Associated Links Section -->
	<div class="card px-6 py-4 bg-white shadow-lg mb-4">
		<h2 class="text-xl font-semibold mb-4">{m.associatedObjects()}</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			{#each Object.entries(validation_flow) as [key, value]}
				{#if Array.isArray(value) && value.length > 0 && modelDisplayNames[key]}
					<div class="space-y-2">
						<h3 class="text-sm font-medium text-gray-700">{modelDisplayNames[key]}</h3>
						<div class="space-y-2">
							{#each value as item}
								<div class="border rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition">
									<div class="flex items-start justify-between gap-2 mb-2">
										<Anchor
											href="/{modelUrlNames[key]}/{item.id}"
											class="anchor text-sm font-medium"
										>
											{item.str}
										</Anchor>
										{#if item.status}
											<span
												class="badge {statusColors[item.status] ||
													'bg-gray-100 text-gray-800'} px-2 py-1 rounded text-xs font-medium whitespace-nowrap flex-shrink-0"
											>
												{safeTranslate(item.status)}
											</span>
										{/if}
									</div>
									<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
										{#if item.perimeter}
											<div class="flex items-center gap-1">
												<i class="fa-solid fa-draw-polygon text-gray-400"></i>
												<span>{m.perimeter()}:</span>
												<Anchor href="/perimeters/{item.perimeter.id}" class="anchor">
													{item.perimeter.str}
												</Anchor>
											</div>
										{/if}
										{#if item.updated_at}
											<div class="flex items-center gap-1">
												<i class="fa-solid fa-clock text-gray-400"></i>
												<span>{m.lastUpdate()}:</span>
												<span>{formatDateOrDateTime(item.updated_at, getLocale())}</span>
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			{/each}
		</div>
	</div>
</div>

<!-- Events History Section -->
{#if validation_flow.events && validation_flow.events.length > 0}
	<div class="card px-6 py-4 bg-white shadow-lg">
		<h2 class="text-xl font-semibold mb-4">{m.eventsHistory()}</h2>
		<div class="space-y-4">
			{#each validation_flow.events as event}
				<div class="border-l-4 border-primary-500 pl-4 py-2">
					<div class="flex justify-between items-start mb-2">
						<div>
							<span
								class="badge {statusColors[event.event_type] ||
									'bg-gray-100 text-gray-800'} px-2 py-1 rounded text-xs font-medium mr-2"
							>
								{safeTranslate(event.event_type)}
							</span>
							<span class="text-sm font-medium text-gray-700">
								{#if event.event_actor}
									{#if event.event_actor.first_name || event.event_actor.last_name}
										{event.event_actor.first_name}
										{event.event_actor.last_name}
									{:else}
										{event.event_actor.email}
									{/if}
								{/if}
							</span>
						</div>
						<div class="text-xs text-gray-500">
							{formatDateOrDateTime(event.created_at, getLocale())}
						</div>
					</div>
					{#if event.event_notes}
						<div class="text-sm text-gray-600">
							<MarkdownRenderer content={event.event_notes} />
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</div>
{/if}

<!-- Observation Modal -->
{#if showObservationModal}
	<div
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
		onclick={closeObservationModal}
	>
		<div
			class="card p-6 bg-white shadow-2xl max-w-2xl w-full mx-4"
			onclick={(e) => e.stopPropagation()}
		>
			<div class="flex justify-between items-start mb-4">
				<h2 class="text-xl font-bold capitalize">
					{#if currentAction === 'approve'}
						{m.approve()}
					{:else if currentAction === 'reject'}
						{m.reject()}
					{:else if currentAction === 'revoke'}
						{m.revoke()}
					{:else if currentAction === 'drop'}
						{m.drop()}
					{:else if currentAction === 'request_changes'}
						{m.requestChanges()}
					{:else if currentAction === 'resubmit'}
						{m.resubmit()}
					{/if}
				</h2>
				<button
					type="button"
					class="text-gray-500 hover:text-gray-700"
					onclick={closeObservationModal}
				>
					<i class="fa-solid fa-times text-xl"></i>
				</button>
			</div>

			<div class="space-y-4">
				<div>
					<label for="observation" class="block text-sm font-medium text-gray-700 mb-2">
						{m.notes()}
					</label>
					<textarea
						id="observation"
						bind:value={notes}
						class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
						rows="4"
						placeholder={m.enterYourObservation()}
					></textarea>
				</div>

				<div class="flex justify-end space-x-2">
					<button
						type="button"
						class="btn preset-filled-surface-500"
						onclick={closeObservationModal}
						disabled={isSubmitting}
					>
						{m.cancel()}
					</button>
					<button
						type="button"
						class="btn {currentAction === 'approve'
							? 'preset-filled-success-500'
							: currentAction === 'reject'
								? 'preset-filled-error-500'
								: currentAction === 'revoke' || currentAction === 'request_changes'
									? 'preset-filled-warning-500'
									: currentAction === 'resubmit'
										? 'preset-filled-primary-500'
										: 'preset-filled-surface-500'}"
						onclick={handleConfirmAction}
						disabled={isSubmitting}
					>
						{#if isSubmitting}
							<i class="fa-solid fa-spinner fa-spin mr-2"></i>
						{:else}
							<i
								class="fa-solid {currentAction === 'approve'
									? 'fa-check'
									: currentAction === 'reject'
										? 'fa-times'
										: currentAction === 'revoke'
											? 'fa-ban'
											: currentAction === 'drop'
												? 'fa-trash'
												: currentAction === 'request_changes'
													? 'fa-pencil'
													: 'fa-paper-plane'} mr-2"
							></i>
						{/if}
						{m.confirm()}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
