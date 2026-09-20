<script lang="ts">
	import type { Snippet } from 'svelte';
	import BackgroundCheckbox, { type CheckboxAccent } from './BackgroundCheckbox.svelte';
	import type { FeatureFlagGroup } from '$lib/utils/feature-flag-groups';

	interface Props {
		groups: FeatureFlagGroup[];
		/** Controlled by the caller: the instance form reads a superform store, the
		 * profile page reads its own state and PATCHes on change. */
		isEnabled: (field: string) => boolean;
		onToggle: (field: string, next: boolean) => void;
		/** A flag the caller cannot offer — e.g. a module the organisation disabled,
		 * which a user may not switch back on for themselves. */
		isDisabled?: (field: string) => boolean;
		/** Overrides the flag's own description. */
		helpTextFor?: (field: string, description: string) => string;
		/** Hover hint, chiefly why a disabled flag cannot be toggled. */
		tooltipFor?: (field: string) => string | undefined;
		accent?: CheckboxAccent;
		/** Per-group header controls (bulk enable/disable, counts). */
		groupActions?: Snippet<[FeatureFlagGroup]>;
	}

	let {
		groups,
		isEnabled,
		onToggle,
		isDisabled = () => false,
		helpTextFor = (_field, description) => description,
		tooltipFor = () => undefined,
		accent = 'primary',
		groupActions
	}: Props = $props();
</script>

{#each groups as group (group.category)}
	<div class="bg-surface-50-950 shadow-sm rounded-xl p-6 border border-surface-200-800">
		<div class="mb-4 flex items-start justify-between gap-4">
			<div>
				<h2 class="text-xl font-bold text-surface-950-50">{group.category}</h2>
				<p class="text-sm text-surface-600-400 mt-1">{group.description}</p>
			</div>
			{#if groupActions}
				<div class="flex items-center gap-2 shrink-0">
					{@render groupActions(group)}
				</div>
			{/if}
		</div>
		<div
			class="grid gap-4"
			style="grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); grid-auto-rows: 1fr;"
		>
			{#each group.fields as { field, label, description } (field)}
				<BackgroundCheckbox
					{field}
					{label}
					{accent}
					checked={isEnabled(field)}
					disabled={isDisabled(field)}
					helpText={helpTextFor(field, description)}
					tooltip={tooltipFor(field)}
					onToggle={(next) => onToggle(field, next)}
					classesContainer="h-full"
					classes="h-full"
				/>
			{/each}
		</div>
	</div>
{/each}
