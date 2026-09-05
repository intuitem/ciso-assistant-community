<script lang="ts">
	import { scheduleLabel, type TaskSchedule } from '$lib/utils/taskSchedule';

	interface Props {
		cell: TaskSchedule | null;
		meta?: Record<string, unknown>;
	}

	let { cell, meta }: Props = $props();

	// A one-time task can still carry a schedule, but nothing reads it: node
	// generation is gated on is_recurrent. Showing a cadence there would promise a
	// recurrence that will never happen.
	const label = $derived(meta?.is_recurrent ? scheduleLabel(cell) : null);
</script>

{#if label}
	<span>{label}</span>
{:else}
	<span class="text-surface-600-400">--</span>
{/if}
