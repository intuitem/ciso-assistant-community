<script lang="ts">
	import { slide } from 'svelte/transition';
	import { sineInOut } from 'svelte/easing';

	export let info: any[];
	const today = new Date();

	function getDates() {
		const currentDate = new Date();
		const notifications: { [index: string]: any } = {};

		// Get the 15 previous dates
		for (let i = 15; i > 1; i--) {
			const previousDate = new Date(currentDate);
			previousDate.setDate(currentDate.getDate() - i);
			const formattedDate = previousDate.toISOString().split('T')[0];
			notifications[formattedDate] = [];
		}

		// Get the 15 upcoming dates
		for (let i = 0; i < 15; i++) {
			const upcomingDate = new Date(currentDate);
			upcomingDate.setDate(currentDate.getDate() + i);
			const formattedDate = upcomingDate.toISOString().split('T')[0];
			notifications[formattedDate] = [];
		}

		for (let i = 0; i < info.length; i++) {
			const date = info[i].date.toISOString().split('T')[0];

			if (notifications[date]) {
				notifications[date].push(info[i]);
			}
		}

		return notifications;
	}

	function formatDate(date: string) {
		let literalDate = new Date(date);
		return literalDate.toLocaleDateString('en-US', {
			weekday: 'long',
			month: 'long',
			day: 'numeric'
		});
	}

	const notifications = Object.entries(getDates());
</script>

<div
	transition:slide={{ duration: 500, easing: sineInOut, axis: 'x' }}
	class="flex flex-col text-white rounded-lg bg-gradient-to-r from-secondary-400 to-primary-500 h-full w-1/4 p-2 space-y-3 shadow-xl overflow-y-auto"
>
	<div class="flex flex-row items-center justify-center w-full">
		<h3 class="font-semibold uppercase">Notifications</h3>
	</div>
	<div class="flex flex-col space-y-2 items-center justify-center w-full whitespace-nowrap">
		{#each notifications as [date, infos]}
			{#if infos.length > 0}
				{#if new Date(date).getDate() < today.getDate() && new Date(date).getMonth() <= today.getMonth() && new Date(date).getFullYear() <= today.getFullYear()}
					<div class="flex flex-col items-center justify-center text-red-500">
						<h4 class="font-semibold underline">{formatDate(date)}</h4>
						{#each infos as eta}
							<li>
								<a class="unstyled hover:underline font-light" href={eta.link}>
									{eta.label}
								</a>
							</li>
						{/each}
					</div>
				{:else if new Date(date).getDate() == today.getDate() && new Date(date).getMonth() == today.getMonth()}
					<div class="flex flex-col items-center justify-center">
						<div class="flex flex-row space-x-2 items-center">
							<i class="fas fa-calendar-day" />
							<h4 class="font-semibold underline">{formatDate(date)}</h4>
						</div>
						{#each infos as eta}
							<li>
								<a class="unstyled hover:underline font-light" href={eta.link}>
									{eta.label}
								</a>
							</li>
						{/each}
					</div>
				{:else}
					<h4 class="font-semibold underline">{formatDate(date)}</h4>
					{#each infos as eta}
						<li>
							<a class="unstyled hover:underline font-light" href={eta.link}>
								{eta.label}
							</a>
						</li>
					{/each}
				{/if}
			{/if}
		{/each}
	</div>
</div>
