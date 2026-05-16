<script lang="ts" module>
	export type ExportFormat = 'CSV' | 'XLSX' | 'DOCX' | 'PDF' | 'ZIP' | 'HTML';

	export interface ExportOption {
		titleKey: string;
		descriptionKey?: string;
		format: ExportFormat;
		href: string;
		kind?: 'download' | 'navigate';
		testId?: string;
	}

	export interface ExportGroup {
		titleKey: string;
		options: ExportOption[];
	}
</script>

<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	interface Props {
		parent: any;
		title?: string;
		groups?: ExportGroup[];
	}

	let { parent, title = '', groups = [] }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	const FORMAT_ICON: Record<ExportFormat, string> = {
		CSV: 'fa-file-csv',
		XLSX: 'fa-file-excel',
		DOCX: 'fa-file-word',
		PDF: 'fa-file-pdf',
		ZIP: 'fa-file-zipper',
		HTML: 'fa-file-code'
	};

	const FORMAT_COLOR: Record<ExportFormat, string> = {
		CSV: 'text-emerald-600',
		XLSX: 'text-green-700',
		DOCX: 'text-blue-700',
		PDF: 'text-red-600',
		ZIP: 'text-amber-600',
		HTML: 'text-purple-600'
	};

	function handleClick() {
		modalStore.close();
	}
</script>

{#if $modalStore[0]}
	<div
		class="card bg-surface-50 p-6 w-modal max-w-2xl shadow-xl space-y-5"
		data-testid="export-modal"
	>
		<header class="flex items-center gap-2">
			<i class="fa-solid fa-download text-primary-600"></i>
			<h2 class="text-xl font-bold" data-testid="modal-title">
				{title || m.exportOptionsTitle()}
			</h2>
		</header>

		<div class="space-y-5">
			{#each groups as group}
				{#if group.options.length > 0}
					<section>
						{#if group.titleKey}
							<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
								{safeTranslate(group.titleKey)}
							</h3>
						{/if}
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
							{#each group.options as option}
								<a
									href={option.href}
									onclick={handleClick}
									data-testid={option.testId}
									aria-label={`${safeTranslate(option.titleKey)} — ${option.format}`}
									class="group flex flex-col p-3 rounded-container border border-surface-300 bg-white hover:border-primary-500 hover:bg-primary-50/40 hover:shadow-sm transition-colors"
								>
									<div class="flex items-center gap-2 mb-1">
										<i
											class="fa-solid {FORMAT_ICON[option.format]} {FORMAT_COLOR[
												option.format
											]} text-lg"
										></i>
										<span class="badge preset-tonal-primary text-xs font-semibold">
											{option.format}
										</span>
										{#if option.kind === 'navigate'}
											<i
												class="fa-solid fa-arrow-up-right-from-square ml-auto text-xs text-gray-400"
												aria-hidden="true"
											></i>
										{/if}
									</div>
									<div class="text-sm font-semibold text-gray-900">
										{safeTranslate(option.titleKey)}
									</div>
									{#if option.descriptionKey}
										<div class="text-xs text-gray-500 mt-0.5">
											{safeTranslate(option.descriptionKey)}
										</div>
									{/if}
								</a>
							{/each}
						</div>
					</section>
				{/if}
			{/each}
		</div>

		<footer class="flex justify-end pt-2">
			<button type="button" class="btn preset-tonal" onclick={parent.onClose}>
				{m.close()}
			</button>
		</footer>
	</div>
{/if}
