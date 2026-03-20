<script lang="ts">
	interface Props {
		diff: string;
	}

	let { diff }: Props = $props();

	let lines = $derived(diff ? diff.split('\n') : []);

	function getLineClass(line: string): string {
		if (line.startsWith('+++') || line.startsWith('---')) return 'bg-surface-100 text-surface-500';
		if (line.startsWith('@@')) return 'bg-blue-50 text-blue-500 font-medium';
		if (line.startsWith('+')) return 'bg-emerald-50 text-emerald-800';
		if (line.startsWith('-')) return 'bg-red-50 text-red-800';
		return 'text-surface-600';
	}

	function getGutterClass(line: string): string {
		if (line.startsWith('+') && !line.startsWith('+++')) return 'bg-emerald-100 text-emerald-600';
		if (line.startsWith('-') && !line.startsWith('---')) return 'bg-red-100 text-red-600';
		if (line.startsWith('@@')) return 'bg-blue-100 text-blue-500';
		return 'bg-surface-50 text-surface-400';
	}

	function getLineIcon(line: string): string {
		if (line.startsWith('+') && !line.startsWith('+++')) return '+';
		if (line.startsWith('-') && !line.startsWith('---')) return '-';
		if (line.startsWith('@@')) return '@';
		return ' ';
	}
</script>

<div class="card border border-surface-200 overflow-auto flex-1 min-h-[500px]">
	{#if !diff}
		<div class="flex flex-col items-center justify-center h-full p-12 text-surface-400">
			<i class="fa-solid fa-code-compare text-3xl mb-3"></i>
			<p class="text-sm">No differences to display</p>
		</div>
	{:else}
		<div class="text-xs font-mono leading-snug">
			{#each lines as line, i}
				<div class="flex {getLineClass(line)} border-b border-surface-50">
					<span class="w-7 flex-shrink-0 text-center select-none py-px {getGutterClass(line)}">
						{getLineIcon(line)}
					</span>
					<span class="px-3 py-px whitespace-pre-wrap break-all">{line}</span>
				</div>
			{/each}
		</div>
	{/if}
</div>
