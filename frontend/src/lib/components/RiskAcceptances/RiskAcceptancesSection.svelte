<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDate } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime';
	import { m } from '$paraglide/messages';

	interface Approver {
		id: string;
		first_name?: string;
		last_name?: string;
		str?: string;
	}

	interface RiskAcceptance {
		id: string;
		name: string;
		// Human-readable state from the API (Created/Submitted/Accepted/Rejected/Revoked)
		state: string;
		approver: Approver | null;
		expiry_date?: string | null;
		justification?: string | null;
	}

	interface Props {
		riskAcceptances: RiskAcceptance[];
	}

	let { riskAcceptances }: Props = $props();

	function getStatusIcon(state: string): string {
		switch (state) {
			case 'Accepted':
				return 'fa-check-circle text-green-600';
			case 'Rejected':
			case 'Revoked':
				return 'fa-times-circle text-red-600';
			case 'Submitted':
				return 'fa-paper-plane text-blue-600';
			default:
				return 'fa-pen-to-square text-surface-600-400';
		}
	}

	function getApproverName(approver: RiskAcceptance['approver']): string {
		if (!approver) return m.undefined();
		if (approver.first_name || approver.last_name) {
			return `${approver.first_name || ''} ${approver.last_name || ''}`.trim();
		}
		return approver.str ?? m.undefined();
	}
</script>

{#if riskAcceptances && riskAcceptances.length > 0}
	<Dropdown
		header={m.riskAcceptances()}
		icon="fa-solid fa-signature"
		style="hover:text-primary-700"
		open={false}
		compact
	>
		<div
			class="grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-3 overflow-y-auto pr-1 max-h-96"
		>
			{#each riskAcceptances as riskAcceptance}
				<div class="p-3 bg-surface-50-950 rounded-lg border border-surface-200-800">
					<div class="flex items-center space-x-2 mb-2">
						<Anchor
							href="/risk-acceptances/{riskAcceptance.id}"
							class="anchor font-medium"
							data-testid="risk-acceptance-link"
						>
							{riskAcceptance.name}
						</Anchor>
						<span
							class="badge text-xs"
							class:preset-tonal-success={riskAcceptance.state === 'Accepted'}
							class:preset-tonal-error={riskAcceptance.state === 'Rejected' ||
								riskAcceptance.state === 'Revoked'}
							class:preset-tonal-secondary={riskAcceptance.state === 'Submitted' ||
								riskAcceptance.state === 'Created'}
						>
							{safeTranslate(riskAcceptance.state)}
						</span>
						<i class="fa-solid {getStatusIcon(riskAcceptance.state)} text-sm ml-1"></i>
					</div>
					<div class="text-sm text-surface-600-400">
						<i class="fa-solid fa-user-check mr-1"></i>
						<span class="font-medium">{m.approver()}:</span>
						{getApproverName(riskAcceptance.approver)}
					</div>
					{#if riskAcceptance.expiry_date}
						<div class="text-sm text-surface-600-400 mt-1">
							<i class="fa-solid fa-calendar-xmark mr-1"></i>
							<span class="font-medium">{m.expiryDate()}:</span>
							{formatDate(new Date(riskAcceptance.expiry_date), false, getLocale())}
						</div>
					{/if}
					{#if riskAcceptance.justification}
						<div class="text-sm text-surface-600-400 mt-1">
							<i class="fa-solid fa-note-sticky mr-1"></i>
							<span class="font-medium">{m.justification()}:</span>
							<span class="whitespace-pre-line">{riskAcceptance.justification}</span>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</Dropdown>
{/if}
