<script lang="ts">
	import { fly } from 'svelte/transition';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	export let day: number;
	export let month: number;
	export let year: number;
	export let info: any[];
	export let selectedDay;
	export let showSidePanel;

	const today = new Date();
	const MAX_ITEMS = 3;

	$: isToday =
		day === today.getDate() && month === today.getMonth() + 1 && year === today.getFullYear();

	$: isPast =
		year < today.getFullYear() ||
		(year === today.getFullYear() && month < today.getMonth() + 1) ||
		(year === today.getFullYear() && month === today.getMonth() + 1 && day < today.getDate());

	$: dayInfo = info.filter(
		(item) =>
			item.date.getDate() === day &&
			item.date.getMonth() + 1 === month &&
			item.date.getFullYear() === year
	);

	$: visibleItems = dayInfo.slice(0, MAX_ITEMS);

	$: extraItemsCount = Math.max(0, dayInfo.length - MAX_ITEMS);

	function openSidePanel() {
		selectedDay.set({ day, month, year });
		showSidePanel.set(true);
	}

	function truncateLabel(label: string, maxLength: number): string {
		if (label.length <= maxLength) {
			return label;
		}
		return label.slice(0, maxLength) + '...';
	}
</script>

{#key month}
	<button
		in:fly={{ delay: 100, duration: 300 }}
		class="flex flex-col p-1 rounded-md text-sm h-[8rem] max-h-[8rem] border
		       {isPast
			? 'bg-gray-300 text-gray-500 cursor-pointer hover:bg-gray-400'
			: 'border-gray-200 bg-white cursor-pointer hover:bg-gray-100'} 
		       {isToday ? 'border-gray-200 cursor-pointer hover:bg-gray-100' : ''}"
		on:click={openSidePanel}
	>
		<span
			class={isToday ? 'font-bold bg-primary-500 w-fit text-white rounded-full py-0.5 px-1' : ''}
			>{day}</span
		>

		{#if dayInfo.length > 0}
			<div class="flex flex-col justify-center h-full w-full space-y-1">
				{#each visibleItems as item}
					<span
						class="flex justify-center cursor-pointer unstyled px-1 rounded-md border-l-2
						{item.color === 'primary'
							? 'hover:bg-primary-200 text-primary-700 bg-primary-50 border-l-primary-500'
							: ''}
						{item.color === 'secondary'
							? 'hover:bg-green-200 text-green-700 bg-green-50 border-l-green-500'
							: ''}
						{item.color === 'tertiary'
							? 'hover:bg-tertiary-200 text-tertiary-700 bg-tertiary-50 border-l-tertiary-500'
							: ''}
						"
					>
						<Anchor href={item.link} stopPropagation={true}>
							{#if $showSidePanel}
								{truncateLabel(item.label, 15)}
							{:else}
								{truncateLabel(item.label, 25)}
							{/if}
						</Anchor>
					</span>
				{/each}

				{#if extraItemsCount > 0}
					<button
						class="flex justify-center font-bold unstyled hover:bg-primary-200 text-primary-700 bg-primary-50 px-1 rounded-md"
						on:click|stopPropagation={() => {
							openSidePanel();
						}}
					>
						+{extraItemsCount}
					</button>
				{/if}
			</div>
		{/if}
	</button>
{/key}
