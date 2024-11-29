<script lang="ts">
	import * as m from '$paraglide/messages';

	export let title = 'activity';
	export let status = '';
	export let meta = [];
</script>

<div class="rounded bg-white p-4 flex flex-col justify-between">
	<div class="flex justify-between mb-2">
		<div class="font-semibold">{title}</div>
		<div class="text-xl">
			{#if status == 'to_do'}
				<i class="fa-solid fa-exclamation"></i>
			{:else if status == 'in_progress'}
				<i class="fa-solid fa-spinner"></i>
			{:else if status == 'done'}
				<i class="fa-solid fa-check"></i>
			{/if}
		</div>
	</div>
	{#each meta as kv}
		<div class="mt-2">{kv}</div>
	{/each}
	<div class="justify-end flex">
		<div class="text-xl text-zinc-700"><i class="fa-solid fa-play"></i></div>
	</div>
</div>
