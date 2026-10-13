<script lang="ts">
	// A computed metric's formula, edited beside the metric: no backdrop, so
	// the page stays readable while the drawer shows the new line against the
	// metric as it is now.
	import { fly } from 'svelte/transition';
	import ComposeMetricEditor, { type Composition, type Saved } from './ComposeMetricEditor.svelte';

	interface Props {
		instanceId: string;
		// Null: the drawer is closed.
		composition: Composition | null;
		onClose: () => void;
		onSaved: (saved: Saved) => void;
	}

	let { instanceId, composition, onClose, onSaved }: Props = $props();
</script>

{#if composition}
	<aside
		class="fixed top-0 right-0 bottom-0 z-50 flex flex-col bg-surface-50-950 border-l-2 border-surface-300-700
			shadow-[-16px_0_48px_-12px_rgba(2,6,23,0.38)] dark:shadow-[-16px_0_48px_-12px_rgba(0,0,0,0.75)]"
		style="width: min(34rem, 100vw)"
		transition:fly={{ x: 420, duration: 220 }}
		role="dialog"
		aria-modal="false"
		aria-label={composition.name}
		data-testid="formula-drawer"
	>
		<ComposeMetricEditor
			layout="drawer"
			{instanceId}
			{composition}
			{onClose}
			onSaved={(saved) => {
				onSaved(saved);
				onClose();
			}}
		/>
	</aside>
{/if}
