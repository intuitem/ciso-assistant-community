<script lang="ts">
	interface Props {
		diff: string;
	}

	let { diff }: Props = $props();

	let lines = $derived(diff ? diff.split('\n') : []);

	function getLineClass(line: string): string {
		if (line.startsWith('+++') || line.startsWith('---')) return 'bg-gray-100 text-gray-600';
		if (line.startsWith('@@')) return 'bg-blue-50 text-blue-600';
		if (line.startsWith('+')) return 'bg-green-50 text-green-700';
		if (line.startsWith('-')) return 'bg-red-50 text-red-700';
		return 'text-gray-700';
	}

	function getLineIcon(line: string): string {
		if (line.startsWith('+') && !line.startsWith('+++')) return '+';
		if (line.startsWith('-') && !line.startsWith('---')) return '-';
		return ' ';
	}
</script>

<div class="border rounded-lg bg-white overflow-auto flex-1 min-h-[500px]">
	{#if !diff}
		<div class="p-8 text-center text-gray-400">
			<i class="fa-solid fa-code-compare text-4xl mb-4"></i>
			<p>No differences to display</p>
		</div>
	{:else}
		<pre class="text-sm p-0 m-0"><code
				>{#each lines as line, i}<div
						class="px-4 py-0.5 font-mono text-xs border-b border-gray-50 {getLineClass(line)}"><span
							class="inline-block w-4 text-center select-none opacity-50">{getLineIcon(line)}</span
						><span class="ml-2">{line}</span></div>{/each}</code
			></pre>
	{/if}
</div>
