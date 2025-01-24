<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { popup, type PopupSettings } from '@skeletonlabs/skeleton';

	export let cell;
	export let cellData: Array<any> = [];
	export let dataItemComponent;
	export let useBubbles = true;
	export let popupTarget: string | undefined = undefined;

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

	let popupClick: PopupSettings;
	if (cellData.length && popupTarget) {
		popupClick = {
			event: 'click',
			target: popupTarget,
			placement: 'top'
		};
	}

	$: classesBubbleSize = (itemCount: number) => {
		for (const range of bubbleSizeRanges) {
			if (itemCount <= range.max) {
				return `width: ${range.value}rem; height: ${range.value}rem`;
			}
		}
		return `width: ${maxBubbleSize}rem; height: ${maxBubbleSize}rem`;
	};
	$: classesCellText = (backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	};
</script>

{#if useBubbles && cellData.length >= bubbleMinCount && dataItemComponent}
	<div
		class="flex flex-wrap items-center space-x-1 justify-center h-full cursor-pointer whitespace-normal overflow-y-scroll hide-scrollbar group {classesCellText(
			cell.level.hexcolor
		)}"
		style="background-color: {cell.level.hexcolor};"
		data-testid="cell"
		use:popup={popupClick}
	>
		<div
			class="bg-surface-900/70 rounded-full flex justify-center items-center text-center text-white transition-colors group-hover:bg-surface-900/100 duration-300"
			style="{classesBubbleSize(cellData.length)};"
		>
			{cellData.length}
		</div>
		<div class="card bg-surface-300 text-black z-20" data-popup={popupTarget}>
			<div class="max-h-56 overflow-y-scroll p-4">
				{#each cellData as item}
					<svelte:component this={dataItemComponent} data={item} />
				{/each}
				<div class="arrow bg-surface-300" />
			</div>
		</div>
	</div>
{:else}
	<div
		class="flex flex-wrap flex-col items-center justify-center h-full [&>*]:pointer-events-none whitespace-normal overflow-y-scroll hide-scrollbar {classesCellText(
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
{/if}
