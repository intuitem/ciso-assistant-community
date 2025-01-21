<script lang="ts">
	import { isDark } from '$lib/utils/helpers';

	export let cell;
	export let cellData = [];
	export let dataItemComponent;

	$: classesCellText = (backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	};
</script>

<div
	class="flex flex-wrap items-center space-x-1 justify-center h-full [&>*]:pointer-events-none whitespace-normal overflow-y-scroll hide-scrollbar {classesCellText(
		cell.level.hexcolor
	)}"
	style="background-color: {cell.level.hexcolor};"
	data-testid="cell"
>
	{#if dataItemComponent}
		{#each cellData as item}
			<svelte:component this={dataItemComponent} data={item} />
		{/each}
	{:else}
		<div class="mx-auto text-center">{cellData}</div>
	{/if}
</div>
