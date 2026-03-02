<script lang="ts">
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const assignmentStatusBadgeStyle: Record<string, string> = {
		draft: 'bg-gray-100 text-gray-600',
		in_progress: 'bg-amber-50 text-amber-700',
		submitted: 'bg-blue-50 text-blue-700',
		closed: 'bg-emerald-50 text-emerald-700',
		changes_requested: 'bg-red-50 text-red-700'
	};

	const statusAccentColor: Record<string, string> = {
		draft: 'border-l-gray-300',
		in_progress: 'border-l-amber-400',
		submitted: 'border-l-blue-400',
		closed: 'border-l-emerald-500',
		changes_requested: 'border-l-red-400'
	};

	const assignmentStatusLabel: Record<string, () => string> = {
		draft: () => m.assignmentStatusDraft(),
		in_progress: () => m.assignmentStatusInProgress(),
		submitted: () => m.assignmentStatusSubmitted(),
		closed: () => m.assignmentStatusClosed(),
		changes_requested: () => m.assignmentStatusChangesRequested()
	};

	function getCtaLabel(audit: { assignment_status?: string; progress_percent: number }): string {
		switch (audit.assignment_status) {
			case 'draft':
				return m.assignmentAwaitingStart();
			case 'submitted':
			case 'closed':
				return m.reviewResponses();
			case 'in_progress':
			case 'changes_requested':
				return audit.progress_percent === 0 ? m.startAssessment() : m.continueAssessment();
			default:
				return audit.progress_percent === 0 ? m.startAssessment() : m.continueAssessment();
		}
	}

	function isCtaDisabled(audit: { assignment_status?: string }): boolean {
		return audit.assignment_status === 'draft';
	}

	function isCtaReadOnly(audit: { assignment_status?: string }): boolean {
		return audit.assignment_status === 'submitted' || audit.assignment_status === 'closed';
	}

	// Group audits by folder (domain)
	const auditsByFolder = $derived.by(() => {
		const groups: Record<string, typeof data.dashboard> = {};
		for (const audit of data.dashboard) {
			const folder = audit.folder ?? m.undefined?.() ?? '--';
			if (!groups[folder]) groups[folder] = [];
			groups[folder].push(audit);
		}
		return Object.entries(groups);
	});
</script>

<div class="flex flex-col space-y-6 p-3">
	{#if data.dashboard.length === 0}
		<div class="flex flex-col items-center justify-center py-20">
			<div class="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-5">
				<i class="fa-solid fa-clipboard-check text-2xl text-gray-300"></i>
			</div>
			<p class="text-gray-400">{m.noAuditAssignments()}</p>
		</div>
	{:else}
		{#each auditsByFolder as [folderName, audits], fi}
			<section class="space-y-3">
				<h3
					class="text-xs font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-2 {fi >
					0
						? 'pt-5 border-t border-gray-200'
						: ''}"
				>
					<i class="fa-solid fa-folder-open"></i>
					{folderName}
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
					{#each audits as audit, ai}
						<div
							class="audit-card card bg-white shadow-sm border-l-[3px] {statusAccentColor[
								audit.assignment_status
							] ??
								'border-l-gray-300'} p-5 flex flex-col space-y-4 hover:shadow-md hover:-translate-y-px transition-all duration-200"
							style="animation-delay: {ai * 50}ms"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="flex-1 min-w-0">
									<h4 class="font-semibold text-[15px] text-gray-900 leading-snug">
										{audit.name}
									</h4>
									{#if audit.framework}
										<p class="text-xs text-gray-500 mt-1 truncate">
											<i class="fa-solid fa-book mr-1 text-gray-400"></i>{audit.framework}
										</p>
									{/if}
									{#if audit.actor}
										<p class="text-xs text-gray-500 mt-0.5 truncate">
											<i class="fa-solid fa-user mr-1 text-gray-400"></i>{audit.actor}
										</p>
									{/if}
								</div>
								<span
									class="flex-shrink-0 text-[11px] font-medium px-2.5 py-1 rounded-full {assignmentStatusBadgeStyle[
										audit.assignment_status
									] ?? 'bg-gray-100 text-gray-600'}"
								>
									{assignmentStatusLabel[audit.assignment_status]?.() ??
										safeTranslate(audit.status)}
								</span>
							</div>

							<div class="flex-1">
								<div class="flex justify-between items-baseline text-xs text-gray-500 mb-1.5">
									<span>{m.progress()}</span>
									<span class="font-semibold text-gray-700 tabular-nums"
										>{audit.assessed_requirements}/{audit.total_requirements}</span
									>
								</div>
								<div class="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
									<div
										class="h-2 rounded-full transition-all duration-500 ease-out"
										style="width: {audit.progress_percent}%; background: linear-gradient(90deg, var(--color-primary-500), var(--color-primary-400));"
									></div>
								</div>
								<p class="text-[11px] text-gray-400 mt-1 tabular-nums">
									{audit.progress_percent}%
								</p>
							</div>

							{#if isCtaDisabled(audit)}
								<button
									class="btn preset-outlined-surface-500 w-full text-center opacity-50"
									disabled
								>
									<i class="fa-solid fa-hourglass-half mr-2 text-xs"></i>
									{getCtaLabel(audit)}
								</button>
							{:else if isCtaReadOnly(audit)}
								<a
									href="/auditee-assessments/{audit.assignment_id}"
									class="btn preset-outlined-primary-500 w-full text-center"
								>
									<i class="fa-solid fa-eye mr-2 text-xs"></i>
									{getCtaLabel(audit)}
								</a>
							{:else}
								<a
									href="/auditee-assessments/{audit.assignment_id}"
									class="btn preset-filled-primary-500 w-full text-center"
								>
									<i class="fa-solid fa-arrow-right mr-2 text-xs"></i>
									{getCtaLabel(audit)}
								</a>
							{/if}
						</div>
					{/each}
				</div>
			</section>
		{/each}
	{/if}
</div>

<style>
	.audit-card {
		animation: card-enter 0.35s ease-out both;
	}
	@keyframes card-enter {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
