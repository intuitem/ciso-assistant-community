<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Determine the type and get the link to the underlying object
	const actorType = data.data.type;
	const specific = data.data.specific;

	const getTypeIcon = (type: string) => {
		switch (type) {
			case 'user':
				return 'fa-solid fa-user';
			case 'team':
				return 'fa-solid fa-users';
			case 'entity':
				return 'fa-solid fa-building';
			default:
				return 'fa-solid fa-question';
		}
	};

	const getTypeUrl = (type: string, id: string) => {
		switch (type) {
			case 'user':
				return `/users/${id}`;
			case 'team':
				return `/teams/${id}`;
			case 'entity':
				return `/entities/${id}`;
			default:
				return '#';
		}
	};
</script>

<div class="flex flex-col space-y-4">
	<div class="card shadow-lg bg-white p-6">
		<div class="flex items-center space-x-4 mb-6">
			<div
				class="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center text-primary-600"
			>
				<i class="{getTypeIcon(actorType)} text-2xl"></i>
			</div>
			<div>
				<h1 class="text-2xl font-bold text-gray-900">{data.data.str}</h1>
				<span
					class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800"
				>
					{safeTranslate(actorType)}
				</span>
			</div>
		</div>

		<div class="flow-root rounded-lg border border-gray-100 py-3 shadow-xs">
			<dl class="-my-3 divide-y divide-gray-100 text-sm">
				<div class="grid grid-cols-1 gap-1 py-3 px-4 even:bg-surface-50 sm:grid-cols-3 sm:gap-4">
					<dt class="font-medium text-gray-900">{m.type()}</dt>
					<dd class="text-gray-700 sm:col-span-2">
						<span class="inline-flex items-center">
							<i class="{getTypeIcon(actorType)} mr-2"></i>
							{safeTranslate(actorType)}
						</span>
					</dd>
				</div>

				{#if specific}
					<div class="grid grid-cols-1 gap-1 py-3 px-4 even:bg-surface-50 sm:grid-cols-3 sm:gap-4">
						<dt class="font-medium text-gray-900">{safeTranslate(actorType)}</dt>
						<dd class="text-gray-700 sm:col-span-2">
							<Anchor
								breadcrumbAction="push"
								href={getTypeUrl(actorType, specific.id)}
								class="anchor"
							>
								{specific.str || specific.name || specific.email}
							</Anchor>
						</dd>
					</div>
				{/if}

				<div class="grid grid-cols-1 gap-1 py-3 px-4 even:bg-surface-50 sm:grid-cols-3 sm:gap-4">
					<dt class="font-medium text-gray-900">{m.refId()}</dt>
					<dd class="text-gray-700 sm:col-span-2 font-mono text-xs">{data.data.id}</dd>
				</div>
			</dl>
		</div>
	</div>
</div>
