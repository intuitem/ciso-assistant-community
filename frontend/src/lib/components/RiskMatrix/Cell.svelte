<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { popup, type PopupSettings } from '@skeletonlabs/skeleton';

	export let cell;
	export let bubbleSizeScale: number = 0;
	export let cellData: Array<any> = [];
	export let dataItemComponent;

	let popupClick: PopupSettings;
	if (cellData.length) {
		popupClick = {
			event: 'click',
			target: 'popup' + 'data' + '-' + cellData.map((e) => e.ref_id).join('-'),
			placement: 'top'
		};
	}

	$: classesBubbleSize = (itemNumber: number) => {
		itemNumber = (itemNumber / bubbleSizeScale) * 9 + 7; // rescaled to 16
		return `width: ${itemNumber / 4}rem; height: ${itemNumber / 4}rem`;
	};
	$: classesCellText = (backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	};
</script>

{#if cellData.length && dataItemComponent}
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
		<div class="mx-auto text-center">{cellData}</div>
	</div>
{/if}
