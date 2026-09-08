<script lang="ts">
	import { evidenceFileDisplay } from '$lib/utils/evidence-files';

	interface Props {
		cell: any;
		meta?: any;
	}

	let { cell }: Props = $props();
	let files = $derived(evidenceFileDisplay(cell));
</script>

{#if files.length}
	<ul class="space-y-1">
		{#each files as file}
			<li class="max-w-80 break-all" title={file.filename}>
				{file.filename}{#if file.size}<span class="ml-2 whitespace-nowrap text-surface-500"
						>({file.size})</span
					>{/if}
			</li>
		{/each}
	</ul>
{/if}
