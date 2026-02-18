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
		<div class="card bg-surface-50-950 shadow-lg p-8 text-center">
			<i class="fa-solid fa-clipboard-check text-4xl text-surface-300-700 mb-4"></i>
			<p class="text-surface-600-400 text-lg">{m.noAuditAssignments()}</p>
		</div>
	{:else}
		{#each auditsByFolder as [folderName, audits]}
			<div class="space-y-3">
				<h3 class="text-base font-semibold text-surface-700-300 flex items-center gap-2">
					<i class="fa-solid fa-sitemap text-surface-400-600"></i>
					{folderName}
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
					{#each audits as audit}
						<div class="card bg-surface-50-950 shadow-lg p-5 flex flex-col space-y-3">
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<h3 class="font-semibold text-base">{audit.name}</h3>
									{#if audit.framework}
										<p class="text-sm text-surface-600-400 mt-0.5">
											<i class="fa-solid fa-book mr-1"></i>
											{audit.framework}
										</p>
									{/if}
								</div>
								<span
									class="text-xs font-medium px-2 py-1 rounded-md {statusBadgeStyle[audit.status] ??
										'bg-surface-200-800 text-surface-700-300'}"
								>
									{safeTranslate(audit.status)}
								</span>
							</div>

							<div class="flex-1">
								<div class="flex justify-between text-sm text-surface-600-400 mb-1">
									<span>{m.progress()}</span>
									<span class="font-medium"
										>{audit.assessed_requirements}/{audit.total_requirements}</span
									>
								</div>
								<div class="w-full bg-surface-200-800 rounded-full h-2.5">
									<div
										class="bg-indigo-500 h-2.5 rounded-full transition-all duration-300"
										style="width: {audit.progress_percent}%"
									></div>
								</div>
								<p class="text-xs text-surface-400-600 mt-1">{audit.progress_percent}%</p>
							</div>

							<a
								href="/auditee-assessments/{audit.id}"
								class="btn preset-filled-primary-500 w-full text-center"
							>
								<i class="fa-solid fa-arrow-right mr-2"></i>
								{audit.progress_percent === 0 ? m.startAssessment() : m.continueAssessment()}
							</a>
						</div>
					{/each}
				</div>
			</div>
		{/each}
	{/if}
</div>
