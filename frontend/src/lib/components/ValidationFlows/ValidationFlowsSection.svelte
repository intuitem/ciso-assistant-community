<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Approver {
		id: string;
		email: string;
		first_name?: string;
		last_name?: string;
	}

	interface ValidationFlow {
		id: string;
		ref_id: string;
		status:
			| 'submitted'
			| 'accepted'
			| 'rejected'
			| 'revoked'
			| 'expired'
			| 'dropped'
			| 'change_requested';
		approver: Approver | null;
		request_notes?: string | null;
		last_event_notes?: string | null;
	}

	interface Props {
		validationFlows: ValidationFlow[];
	}

	let { validationFlows }: Props = $props();

	// Scroll container: track the adjacent detail card so the validations panel grows
	// and shrinks with the "view more / view less" toggle instead of a fixed height.
	let scrollEl: HTMLDivElement | undefined = $state();
	let maxHeight = $state('70vh');

	$effect(() => {
		if (!scrollEl) return;
		const row = scrollEl.closest<HTMLElement>('.flex.flex-row.flex-wrap.gap-4');
		const detailCard = row?.firstElementChild as HTMLElement | undefined;
		if (!detailCard) return;

		// Keep the detail card sized to its own content so it doesn't stretch to our
		// height, which would otherwise create a measure/grow feedback loop.
		const previousAlignSelf = detailCard.style.alignSelf;
		detailCard.style.alignSelf = 'flex-start';

		// Leave room for the dropdown header (~3rem) so the panel matches the card.
		const update = () => {
			maxHeight = `${Math.max(detailCard.clientHeight - 48, 160)}px`;
		};
		update();
		const observer = new ResizeObserver(update);
		observer.observe(detailCard);
		return () => {
			observer.disconnect();
			detailCard.style.alignSelf = previousAlignSelf;
		};
	});

	// Get status icon
	function getStatusIcon(status: string): string {
		switch (status) {
			case 'accepted':
				return 'fa-check-circle text-green-600';
			case 'rejected':
			case 'revoked':
				return 'fa-times-circle text-red-600';
			case 'expired':
				return 'fa-clock text-yellow-600';
			case 'change_requested':
				return 'fa-edit text-orange-600';
			case 'submitted':
				return 'fa-paper-plane text-blue-600';
			case 'dropped':
				return 'fa-circle-stop text-gray-600';
			default:
				return 'fa-question-circle text-gray-600';
		}
	}

	// Get approver display name
	function getApproverName(approver: ValidationFlow['approver']): string {
		if (approver === null) return m.undefined();
		if (approver.first_name || approver.last_name) {
			return `${approver.first_name || ''} ${approver.last_name || ''}`.trim();
		}
		return approver.email;
	}
</script>

{#if validationFlows && validationFlows.length > 0}
	<Dropdown
		header={m.validationFlows()}
		icon="fa-solid fa-check-double"
		style="hover:text-primary-700"
		open={false}
	>
		<div
			bind:this={scrollEl}
			class="space-y-3 overflow-y-auto pr-1"
			style="max-height: {maxHeight}"
		>
			{#each validationFlows as validation_flow}
				<div class="p-3 bg-gray-50 rounded-lg border border-gray-200">
					<div class="flex items-start justify-between">
						<div class="flex-1">
							<div class="flex items-center space-x-2 mb-2">
								<Anchor
									href="/validation-flows/{validation_flow.id}"
									class="anchor font-medium"
									data-testid="validation-flow-link"
								>
									{validation_flow.ref_id}
								</Anchor>
								<span
									class="badge text-xs"
									class:preset-tonal-success={validation_flow.status === 'accepted'}
									class:preset-tonal-error={validation_flow.status === 'rejected' ||
										validation_flow.status === 'revoked'}
									class:preset-tonal-warning={validation_flow.status === 'expired' ||
										validation_flow.status === 'change_requested'}
									class:preset-tonal-secondary={validation_flow.status === 'submitted' ||
										validation_flow.status === 'dropped'}
								>
									{safeTranslate(validation_flow.status)}
								</span>
								<i class="fa-solid {getStatusIcon(validation_flow.status)} text-sm ml-1"></i>
							</div>
							<div class="text-sm text-gray-600">
								<i class="fa-solid fa-user-check mr-1"></i>
								<span class="font-medium">{m.approver()}:</span>
								{getApproverName(validation_flow.approver)}
							</div>
							{#if validation_flow.request_notes}
								<div class="text-sm text-gray-600 mt-1">
									<i class="fa-solid fa-note-sticky mr-1"></i>
									<span class="font-medium">{m.requestNotes()}:</span>
									<span class="whitespace-pre-line">{validation_flow.request_notes}</span>
								</div>
							{/if}
							{#if validation_flow.last_event_notes && validation_flow.status !== 'submitted'}
								<div class="text-sm text-gray-600 mt-1">
									<i class="fa-solid fa-comment-dots mr-1"></i>
									<span class="font-medium">{m.decisionNotes()}:</span>
									<span class="whitespace-pre-line">{validation_flow.last_event_notes}</span>
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>
	</Dropdown>
{/if}
