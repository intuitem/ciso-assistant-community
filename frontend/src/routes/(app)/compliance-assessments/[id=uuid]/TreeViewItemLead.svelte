<script lang="ts">
	// export let status: string;
	export let statusDisplay: string;
	export let statusColor: string;
	export let assessable: boolean;

	const lead = statusDisplay ?? '';

	$: classesText = statusColor === '#000000' ? 'text-white' : '';
</script>

{#if assessable}
	<span class="badge {classesText}" style="background-color: {statusColor};">
		{lead}
	</span>
{/if}
