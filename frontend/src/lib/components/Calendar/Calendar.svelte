<script lang="ts">
	import { fly } from 'svelte/transition';
	import Day from './Day.svelte';
	import { SlideToggle } from '@skeletonlabs/skeleton';
	import { page } from '$app/stores';
	import { showAllEvents } from '$lib/utils/stores';
	import { writable } from 'svelte/store';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	import { m } from '$paraglide/messages';

	export let info: object[];

	const today = new Date();
	export let month = today.getMonth() + 1;
	export let year = today.getFullYear();
	$: daysInMonth = new Date(year, month, 0).getDate();
	$: firstDay = new Date(year, month - 1, 1).getDay();

	// Store pour la gestion du panel latéral
	export const selectedDay = writable(null);
	export const showSidePanel = writable(false);

	// Fonction pour fermer le panel
	function closePanel() {
		$showSidePanel = false;
	}

	// Fonction pour obtenir les items du jour sélectionné
	$: selectedDayItems = $selectedDay
		? filteredInfo.filter(
				(item) =>
					item.date.getDate() === $selectedDay.day &&
					item.date.getMonth() + 1 === $selectedDay.month &&
					item.date.getFullYear() === $selectedDay.year
			)
		: [];

	const daysOfWeek = [
		m.monday(),
		m.tuesday(),
		m.wednesday(),
		m.thursday(),
		m.friday(),
		m.saturday(),
		m.sunday()
	];
	const monthNames = [
		m.january(),
		m.february(),
		m.march(),
		m.april(),
		m.may(),
		m.june(),
		m.july(),
		m.august(),
		m.september(),
		m.october(),
		m.november(),
		m.december()
	];

	function currentMonth() {
		return `/calendar/${today.getFullYear()}/${today.getMonth() + 1}`;
	}

	function nextMonth(year: number, month: number) {
		if (month == 12) {
			return `/calendar/${year + 1}/1`;
		} else {
			return `/calendar/${year}/${month + 1}`;
		}
	}

	function prevMonth(year: number, month: number) {
		if (month == 1) {
			return `/calendar/${year - 1}/12`;
		} else {
			return `/calendar/${year}/${month - 1}`;
		}
	}

	const user = $page.data.user;
	let filteredInfo = info;

	$: {
		if (!$showAllEvents) {
			filteredInfo = info.filter((event) => event.users.some((userObj) => userObj.id === user.id));
		} else {
			filteredInfo = info;
		}
	}
</script>

<div class="flex flex-row h-full space-x-2">
	<div
		class="flex flex-col rounded-lg bg-white h-full {$showSidePanel
			? 'w-2/3'
			: 'w-full'} p-2 space-y-1 shadow-xl"
	>
		<div
			class="flex flex-col items-center justify-center bg-gradient-to-r from-primary-500 to-secondary-400 text-white rounded-lg p-2 text-3xl font-semibold shadow-md"
		>
			<div class="flex flex-row justify-between w-3/4">
				<a class="sticky" href={prevMonth(year, month)}>
					<i class="fas fa-chevron-left" />
				</a>
				{#key month}
					<p in:fly={{ delay: 100, duration: 300 }}>
						{monthNames[month - 1].toUpperCase()}, {year}
					</p>
				{/key}
				<a href={nextMonth(year, month)}>
					<i class="fas fa-chevron-right" />
				</a>
			</div>
		</div>
		<div class="grid grid-cols-7 gap-5 font-semibold">
			{#each daysOfWeek as dayName}
				<div class="flex justify-center">
					{dayName}
				</div>
			{/each}
		</div>
		<div class="grid grid-cols-7 gap-1 h-full">
			{#if firstDay > 0}
				{#each Array.from({ length: firstDay - 1 }, (_, i) => i + 1) as day}
					<div class="" />
				{/each}
			{:else}
				{#each Array.from({ length: 6 }, (_, i) => i + 1) as day}
					<div class="" />
				{/each}
			{/if}
			{#each Array.from({ length: daysInMonth }, (_, i) => i + 1) as day}
				{#key filteredInfo}
					<Day {day} {month} {year} info={filteredInfo} {selectedDay} {showSidePanel} />
				{/key}
			{/each}
		</div>
		<div class="flex flex-col bg-gradient-to-r from-primary-500 to-secondary-400 rounded-lg p-2">
			<div class="flex w-full h-full justify-between items-center">
				<a
					href={currentMonth()}
					class="font-light text-lg border rounded-lg border-white p-2 hover:bg-white text-white hover:text-primary-500 transition duration-300"
				>
					<i class="fas fa-calendar-day" />
					{m.today()}
				</a>
				<SlideToggle name="tasks-toggle" bind:checked={$showAllEvents} active="bg-green-500"
					><span class="text-white font-light text-lg">{m.showAllEvents()}</span></SlideToggle
				>
			</div>
		</div>
	</div>
	{#if $showSidePanel && $selectedDay}
		<div
			class="flex flex-col rounded-lg bg-white h-full w-1/3 p-4 space-y-3 shadow-xl"
			in:fly={{ x: 300, duration: 300 }}
			out:fly={{ x: 300, duration: 300 }}
		>
			<div class="flex justify-between items-center mb-4">
				<h2 class="text-xl font-bold text-primary-700">
					{$selectedDay.day}
					{monthNames[$selectedDay.month - 1]}, {$selectedDay.year}
				</h2>
				<button on:click={closePanel} class="text-gray-500 hover:text-gray-700 focus:outline-none">
					<i class="fas fa-times"></i>
				</button>
			</div>

			<div class="overflow-y-auto flex-grow">
				{#if selectedDayItems.length > 0}
					<ul class="space-y-2">
						{#each selectedDayItems as item}
							<li
								class="p-3 bg-primary-50 rounded-md hover:bg-primary-100 transition duration-200 border-l-2
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
								<Anchor href={item.link} class="block">
									<div class="font-medium">{item.label}</div>
									{#if item.description}
										<div class="text-sm text-gray-600 mt-1">{item.description}</div>
									{/if}
								</Anchor>
							</li>
						{/each}
					</ul>
				{:else}
					<div class="text-center text-gray-500 py-8">
						{m.noEvents()}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
