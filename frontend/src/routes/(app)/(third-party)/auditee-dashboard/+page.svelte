<script lang="ts">
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const statusBadgeStyle: Record<string, string> = {
		planned: 'bg-yellow-100 text-yellow-800',
		in_progress: 'bg-orange-200 text-orange-800',
		in_review: 'bg-blue-500 text-white',
		done: 'bg-cyan-600 text-white',
		deprecated: 'bg-red-400 text-white'
	};

	const assignmentStatusBadgeStyle: Record<string, string> = {
		draft: 'bg-gray-100 text-gray-700',
		in_progress: 'bg-orange-100 text-orange-700',
		submitted: 'bg-blue-100 text-blue-700',
		closed: 'bg-green-100 text-green-700',
		changes_requested: 'bg-red-100 text-red-700'
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

<div class="flex flex-col space-y-4 p-2">
	{#if data.dashboard.length === 0}
		<div class="card bg-white shadow-lg p-8 text-center">
			<i class="fa-solid fa-clipboard-check text-4xl text-gray-300 mb-4"></i>
			<p class="text-gray-500 text-lg">{m.noAuditAssignments()}</p>
		</div>
	{:else}
		{#each auditsByFolder as [folderName, audits]}
			<div class="space-y-3">
				<h3 class="text-base font-semibold text-gray-700 flex items-center gap-2">
					<i class="fa-solid fa-sitemap text-gray-400"></i>
					{folderName}
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
					{#each audits as audit}
						<div class="card bg-white shadow-lg p-5 flex flex-col space-y-3">
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<h3 class="font-semibold text-base">{audit.name}</h3>
									{#if audit.framework}
										<p class="text-sm text-gray-500 mt-0.5">
											<i class="fa-solid fa-book mr-1"></i>
											{audit.framework}
										</p>
									{/if}
									{#if audit.actor}
										<p class="text-sm text-gray-500 mt-0.5">
											<i class="fa-solid fa-user mr-1"></i>
											{audit.actor}
										</p>
									{/if}
								</div>
								<span
									class="text-xs font-medium px-2 py-1 rounded-md {assignmentStatusBadgeStyle[
										audit.assignment_status
									] ?? 'bg-gray-200 text-gray-700'}"
								>
									{assignmentStatusLabel[audit.assignment_status]?.() ??
										safeTranslate(audit.status)}
								</span>
							</div>

							<div class="flex-1">
								<div class="flex justify-between text-sm text-gray-600 mb-1">
									<span>{m.progress()}</span>
									<span class="font-medium"
										>{audit.assessed_requirements}/{audit.total_requirements}</span
									>
								</div>
								<div class="w-full bg-gray-200 rounded-full h-2.5">
									<div
										class="bg-indigo-500 h-2.5 rounded-full transition-all duration-300"
										style="width: {audit.progress_percent}%"
									></div>
								</div>
								<p class="text-xs text-gray-400 mt-1">{audit.progress_percent}%</p>
							</div>

							{#if isCtaDisabled(audit)}
								<button class="btn preset-outlined-surface-500 w-full text-center" disabled>
									<i class="fa-solid fa-hourglass mr-2"></i>
									{getCtaLabel(audit)}
								</button>
							{:else if isCtaReadOnly(audit)}
								<a
									href="/auditee-assessments/{audit.id}?assignment={audit.assignment_id}"
									class="btn preset-outlined-primary-500 w-full text-center"
								>
									<i class="fa-solid fa-eye mr-2"></i>
									{getCtaLabel(audit)}
								</a>
							{:else}
								<a
									href="/auditee-assessments/{audit.id}?assignment={audit.assignment_id}"
									class="btn preset-filled-primary-500 w-full text-center"
								>
									<i class="fa-solid fa-arrow-right mr-2"></i>
									{getCtaLabel(audit)}
								</a>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/each}
	{/if}
</div>
