<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { toCamelCase } from '$lib/utils/locales';
	import { safeTranslate } from '$lib/utils/i18n';
	import { getLocale } from '$paraglide/runtime';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { canPerformAction } from '$lib/utils/access-control';
	import type { PageData } from './$types';

	function filterUserData() {
		const filtered = {};
		const filter = ['id', 'is_active'];
		const sortedKeys = ['last_name', 'first_name', 'email', 'date_joined'];

		sortedKeys.forEach((key) => {
			if (!filter.includes(key) && Object.prototype.hasOwnProperty.call(page.data.user, key)) {
				const str = toCamelCase(key);
				if (key === 'date_joined')
					filtered[str] = new Date(page.data.user[key]).toLocaleString(getLocale());
				else filtered[str] = page.data.user[key];
			}
		});

		return filtered;
	}

	const user = page.data.user;
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: 'user',
		domain: user.root_folder_id
	});

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="flex flex-col bg-white card shadow-lg p-4 space-y-4">
	<div class="flex flex-row items-center justify-between">
		<h1 class="text-xl font-semibold">
			{data.currentUser.first_name}
			{data.currentUser.last_name}
		</h1>
		<div>
			{#if user.is_local}
				<Anchor href="my-profile/change-password" class="btn preset-filled-primary-500 h-fit"
					><i class="fa-solid fa-key mr-2"></i>{m.changePassword()}</Anchor
				>
			{/if}
			{#if canEditObject}
				<Anchor
					href="/users/{data.currentUser.id}/edit?next=/my-profile"
					class="btn preset-filled-primary-500 h-fit"
					><i class="fa-solid fa-pen-to-square mr-2"></i>{m.edit()}</Anchor
				>
			{/if}
			<Anchor href="my-profile/settings" class="btn preset-filled-primary-500 h-fit"
				><i class="fa-solid fa-sliders mr-2"></i>{m.settings()}</Anchor
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
				{#each data.currentUser.user_groups as group}
					<div class="flex flex-row items-center">
						{#if group.builtin}
							<span class="badge preset-tonal-primary mr-2">{m.builtin()}</span>
						{/if}
						<p class="font-semibold text-sm">{group.str}</p>
					</div>
				{/each}
			</div>
		</div>
	</div>
</div>
