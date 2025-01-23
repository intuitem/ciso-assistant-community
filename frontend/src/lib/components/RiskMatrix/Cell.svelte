<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { popup, type PopupSettings } from '@skeletonlabs/skeleton';

	export let cell;
	export let cellData: Array<any> = [];
	export let dataItemComponent;

	const bubbleMinCount = 2;
	const bubbleSizeRanges = [
		{ max: 3, value: 1.5 },
		{ max: 5, value: 2 },
		{ max: 8, value: 2.5 },
		{ max: 13, value: 3 },
		{ max: 21, value: 3.5 },
		{ max: 34, value: 4 },
		{ max: 55, value: 4.25 }
	];

	let popupClick: PopupSettings;
	if (cellData.length) {
		popupClick = {
			event: 'click',
			target: 'popup' + 'data' + '-' + cellData.map((e) => e.ref_id).join('-'),
			placement: 'top'
		};
	}

	$: classesBubbleSize = (itemCount: number) => {
		for (const range of bubbleSizeRanges) {
			if (itemCount <= range.max) {
				return `width: ${range.value}rem; height: ${range.value}rem`;
			}
		}
	};
	$: classesCellText = (backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	};
</script>

{#if cellData.length >= bubbleMinCount && dataItemComponent}
	<div
		class="flex flex-wrap items-center space-x-1 justify-center h-full cursor-pointer whitespace-normal overflow-y-scroll hide-scrollbar {classesCellText(
			cell.level.hexcolor
		)}"
		style="background-color: {cell.level.hexcolor};"
		data-testid="cell"
		use:popup={popupClick}
	>
		<div
			class="bg-surface-900/80 rounded-full flex justify-center items-center text-center text-white"
			style="{classesBubbleSize(cellData.length)};"
		>
			{cellData.length}
		</div>
		<div
			class="card bg-black text-gray-200 p-4 z-20"
			data-popup={'popup' + 'data' + '-' + cellData.map((e) => e.ref_id).join('-')}
		>
			{#each cellData as item}
				<svelte:component this={dataItemComponent} data={item} />
			{/each}
			<div class="arrow bg-black" />
		</div>
	</div>
{:else}
	<div
		class="flex flex-wrap items-center space-x-1 justify-center h-full [&>*]:pointer-events-none whitespace-normal overflow-y-scroll hide-scrollbar {classesCellText(
			cell.level.hexcolor
		)}"
		style="background-color: {cell.level.hexcolor};"
		data-testid="cell"
	>
		{#if cellData.length}
			{#each cellData as item}
				<svelte:component this={dataItemComponent} data={item} />
			{/each}
		{:else}
			<div class="mx-auto text-center">{cellData}</div>
		{/if}
	</div>
{/if}
