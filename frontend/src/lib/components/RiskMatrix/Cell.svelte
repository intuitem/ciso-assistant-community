<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { Popover } from '@skeletonlabs/skeleton-svelte';

	interface Props {
		cell: any;
		cellData?: Array<any>;
		dataItemComponent: any;
		useBubbles?: boolean;
	}

	let { cell, cellData = [], dataItemComponent, useBubbles = true }: Props = $props();

	const bubbleMinCount = 1;
	const maxBubbleSize = 4.5;
	const bubbleSizeRanges = [
		{ max: 3, value: 1.5 },
		{ max: 5, value: 2 },
		{ max: 8, value: 2.5 },
		{ max: 13, value: 3 },
		{ max: 21, value: 3.5 },
		{ max: 34, value: 4 }
	];

	let open = $state(false);

	let classesBubbleSize = $derived((itemCount: number) => {
		for (const range of bubbleSizeRanges) {
			if (itemCount <= range.max) {
				return `width: ${range.value}rem; height: ${range.value}rem`;
			}
		}
		return `width: ${maxBubbleSize}rem; height: ${maxBubbleSize}rem`;
	});
	let classesCellText = $derived((backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	});
</script>

{#if useBubbles && cellData.length >= bubbleMinCount && dataItemComponent}
	<Popover
		{open}
		onOpenChange={(e) => (open = e.open)}
		triggerBase="w-full h-full"
		positioning={{ placement: 'top', offset: { mainAxis: 0, crossAxis: 0 } }}
		arrow
	>
		{#snippet trigger()}
			<div
				class="flex flex-wrap items-center space-x-1 justify-center w-full h-full cursor-pointer whitespace-normal overflow-y-scroll hide-scrollbar group {classesCellText(
					cell.level.hexcolor
				)}"
				style="background-color: {cell.level.hexcolor};"
				data-testid="cell"
			>
				<div
					class="bg-surface-900/70 rounded-full flex justify-center items-center text-center text-white transition-colors group-hover:bg-surface-900/100 duration-100"
					style="{classesBubbleSize(cellData.length)};"
				>
					{cellData.length}
				</div>
			</div>
		{/snippet}
		{#snippet content()}
			<div class="card bg-surface-300">
				<div class="p-4 max-h-56 overflow-y-auto">
					{#each cellData as item}
						{@const SvelteComponent = dataItemComponent}
						<SvelteComponent data={item} />
					{/each}
					<div class="arrow bg-surface-300"></div>
				</div>
			</div>
		{/snippet}
	</Popover>
{:else}
	<div
		class="flex flex-wrap flex-col items-center justify-center h-full *:pointer-events-none whitespace-normal overflow-y-scroll hide-scrollbar {classesCellText(
			cell.level.hexcolor
		)}"
		style="background-color: {cell.level.hexcolor};"
		data-testid="cell"
	>
		{#if dataItemComponent}
			{#each cellData as item}
				{@const SvelteComponent_1 = dataItemComponent}
				<SvelteComponent_1 data={item} />
			{/each}
		{:else}
			<div class="mx-auto text-center">{cellData}</div>
		{/if}
	</div>
{/if}
