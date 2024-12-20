<script lang="ts">
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages';
	import { toCamelCase } from '$lib/utils/locales';
	import { safeTranslate } from '$lib/utils/i18n';
	import { languageTag } from '$paraglide/runtime';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	function filterUserData() {
		const filtered = {};
		const filter = ['id', 'is_active'];
		const sortedKeys = ['last_name', 'first_name', 'email', 'date_joined'];

		sortedKeys.forEach((key) => {
			if (!filter.includes(key) && Object.prototype.hasOwnProperty.call($page.data.user, key)) {
				const str = toCamelCase(key);
				if (key === 'date_joined')
					filtered[str] = new Date($page.data.user[key]).toLocaleString(languageTag());
				else filtered[str] = $page.data.user[key];
			}
		});

		return filtered;
	}

	const user = $page.data.user;
	const canEditObject: boolean = Object.hasOwn(user.permissions, `change_user`);
</script>

<div class="flex flex-col bg-white card shadow-lg p-4 space-y-4">
	<div class="flex flex-row items-center justify-between">
		<h1 class="text-xl font-semibold">{$page.data.user.first_name} {$page.data.user.last_name}</h1>
		<div>
			<Anchor href="my-profile/change-password" class="btn variant-filled-primary h-fit"
				><i class="fa-solid fa-key mr-2" />{m.changePassword()}</Anchor
			>
			{#if canEditObject}
				<Anchor
					href="/users/{$page.data.user.id}/edit?next=/my-profile"
					class="btn variant-filled-primary h-fit"
					><i class="fa-solid fa-pen-to-square mr-2" />{m.edit()}</Anchor
				>
			{/if}
			<Anchor href="my-profile/settings" class="btn variant-filled-primary h-fit"
				><i class="fa-solid fa-sliders mr-2" />{m.settings()}</Anchor
			>
		</div>
	</div>
	<div class="flex flex-row w-full space-x-2">
		<div class="flex flex-col w-1/2 card bg-white p-2 space-y-4">
			{#each Object.entries(filterUserData()) as [label, value]}
				<div class="flex flex-col">
					<p class="font-semibold text-sm">{safeTranslate(label)}</p>
					<p class="text-sm">{value}</p>
				</div>
			{/each}
		</div>
		<div class="flex flex-col w-1/2 card bg-white p-2 space-y-4">
			<h2 class="text-xl mb-1 font-semibold">{m.myUserGroups()}</h2>
			<div class="overflow-auto space-y-2">
				{#each $page.data.user.user_groups as group}
					<div class="flex flex-row items-center">
						{#if group[1]}
							<span class="badge variant-soft-primary mr-2">{m.builtin()}</span>
						{/if}
						<p class="font-semibold text-sm">{group[0]}</p>
					</div>
				{/each}
			</div>
		</div>
	</div>
</div>
