<script lang="ts">
	interface Props {
		open: boolean;
		onClose: () => void;
	}
	let { open = $bindable(), onClose }: Props = $props();

	// Detect platform for modifier-key labels
	const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);
	const cmdKey = isMac ? '⌘' : 'Ctrl';
	const altKey = isMac ? '⌥' : 'Alt';
	const shiftKey = isMac ? '⇧' : 'Shift';

	const groups = [
		{
			title: 'Outline editing',
			hint: 'Apply to the last node you focused.',
			shortcuts: [
				{ keys: [altKey, '→'], label: 'Indent node' },
				{ keys: [altKey, '←'], label: 'Outdent node' },
				{ keys: [altKey, 'Enter'], label: 'Add child' },
				{ keys: [altKey, shiftKey, 'Enter'], label: 'Add sibling below' },
				{ keys: [cmdKey, '.'], label: 'Toggle assessable' }
			]
		},
		{
			title: 'Builder',
			hint: null,
			shortcuts: [
				{ keys: [cmdKey, 'S'], label: 'Save draft' },
				{ keys: ['?'], label: 'Show this cheatsheet' },
				{ keys: ['Esc'], label: 'Close dialog or dropdown' }
			]
		}
	];
</script>

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
		role="dialog"
		aria-modal="true"
		aria-labelledby="keyboard-help-title"
		onclick={onClose}
		onkeydown={(e) => e.key === 'Escape' && onClose()}
	>
		<div
			class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden"
			onclick={(e) => e.stopPropagation()}
			role="document"
		>
			<div class="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
				<h3 id="keyboard-help-title" class="text-lg font-semibold text-gray-900">
					Keyboard shortcuts
				</h3>
				<button
					type="button"
					class="text-gray-400 hover:text-gray-600 transition-colors"
					aria-label="Close"
					onclick={onClose}
				>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</div>

			<div class="px-5 py-4 space-y-5 text-sm">
				{#each groups as g}
					<div>
						<div class="flex items-baseline justify-between mb-2">
							<h4 class="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
								{g.title}
							</h4>
							{#if g.hint}
								<span class="text-[11px] text-gray-400">{g.hint}</span>
							{/if}
						</div>
						<dl class="space-y-2">
							{#each g.shortcuts as s}
								<div class="flex items-center justify-between gap-6">
									<dt class="text-gray-600">{s.label}</dt>
									<dd class="flex items-center gap-1 shrink-0">
										{#each s.keys as k, i}
											{#if i > 0}
												<span class="text-gray-300 text-xs">+</span>
											{/if}
											<kbd
												class="inline-flex items-center justify-center min-w-[1.75rem] px-1.5 py-0.5 text-xs font-mono font-medium text-gray-700 bg-gray-100 border border-gray-200 rounded"
											>
												{k}
											</kbd>
										{/each}
									</dd>
								</div>
							{/each}
						</dl>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
