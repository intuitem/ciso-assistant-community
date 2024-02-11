<script lang="ts">
	import { page } from '$app/stores';

	function filterUserData() {
		const filtered = {};
		const filter = ['id', 'is_active'];
		const sortedKeys = ['last_name', 'first_name', 'email', 'date_joined'];

		sortedKeys.forEach((key) => {
			if (!filter.includes(key) && Object.prototype.hasOwnProperty.call($page.data.user, key)) {
				const str = key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ');
				if (key === 'date_joined') filtered[str] = new Date($page.data.user[key]).toLocaleString();
				else filtered[str] = $page.data.user[key];
			}
		});

		return filtered;
	}
</script>

<div class="flex flex-col bg-white rounded-lg shadow-lg px-2 pb-4">
	<div class="flex flex-row items-center justify-between p-2">
		<h1 class="text-xl font-semibold">{$page.data.user.first_name} {$page.data.user.last_name}</h1>
		<div>
			<a href="profile/change-password" class="btn variant-filled-primary h-fit"
				><i class="fa-solid fa-key mr-2" />Change password</a
			>
			<a href="/users/{$page.data.user.id}/edit" class="btn variant-filled-primary h-fit"
				><i class="fa-solid fa-pen-to-square mr-2" />Edit</a
			>
		</div>
	</div>
	<div class="flex flex-row w-full space-x-2">
		<div class="flex flex-col w-1/2 border p-2 rounded-lg shadow-lg space-y-4">
			{#each Object.entries(filterUserData()) as [label, value]}
				<div class="flex flex-col">
					<p class="font-semibold text-sm">{label}</p>
					<p class="text-sm">{value}</p>
				</div>
			{/each}
		</div>
		<div class="flex flex-col w-1/2 border p-2 rounded-lg shadow-lg space-y-4">
			<h2 class="text-xl mb-1 font-semibold">My users groups</h2>
			<div class="overflow-auto space-y-2">
				{#each $page.data.user.user_groups as group}
					<div class="flex flex-row items-center">
						{#if group[1]}
							<span class="bg-primary-300 p-1 rounded-lg font-medium text-xs mr-2">builtin</span>
						{/if}
						<p class="font-semibold text-sm">{group[0]}</p>
					</div>
				{/each}
			</div>
		</div>
	</div>
</div>
