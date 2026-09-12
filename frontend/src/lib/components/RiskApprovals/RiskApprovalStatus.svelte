<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	type ApprovalStage = 'assessment' | 'treatment' | 'residual_acceptance';
	type RiskApprovalSummary = Record<ApprovalStage, string>;

	let {
		summary,
		cell,
		compact = false
	}: {
		summary?: RiskApprovalSummary;
		cell?: RiskApprovalSummary;
		compact?: boolean;
		[key: string]: unknown;
	} = $props();
	const value = $derived(summary ?? cell);

	const stages: { key: ApprovalStage; label: string }[] = $derived([
		{ key: 'assessment', label: m.riskApprovalAssessment() },
		{ key: 'treatment', label: m.riskApprovalTreatment() },
		{ key: 'residual_acceptance', label: m.riskApprovalResidualAcceptance() }
	]);

	function statusLabel(status: string): string {
		if (status === 'not_requested') return m.riskApprovalNotRequested();
		if (status === 'not_required') return m.riskApprovalNotRequired();
		if (status === 'outdated') return m.riskApprovalOutdated();
		if (status === 'waiting_for_treatment') return m.riskApprovalWaitingForTreatment();
		if (status === 'tolerance_required') return m.riskApprovalToleranceMissingShort();
		return safeTranslate(status);
	}

	function statusClass(status: string): string {
		if (status === 'accepted' || status === 'not_required') return 'preset-tonal-success';
		if (status === 'submitted' || status === 'change_requested') return 'preset-tonal-warning';
		if (['rejected', 'revoked', 'dropped', 'outdated'].includes(status)) {
			return 'preset-tonal-error';
		}
		return 'preset-tonal-surface';
	}
</script>

{#if value}
	<div class="flex flex-col gap-1" data-testid="risk-approval-status">
		{#each stages as item (item.key)}
			<div class="flex items-center justify-between gap-2 {compact ? 'text-xs' : 'text-sm'}">
				<span>{item.label}</span>
				<span class="badge whitespace-nowrap {statusClass(value[item.key])}">
					{statusLabel(value[item.key])}
				</span>
			</div>
		{/each}
	</div>
{/if}
