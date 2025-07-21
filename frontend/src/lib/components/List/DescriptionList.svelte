<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { getCookie } from '$lib/utils/cookies';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { isURL } from '$lib/utils/helpers';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { toCamelCase } from '$lib/utils/locales.js';
	import * as m from '$paraglide/messages.js';
	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';

	// Passing data directly instead of dividing it in multiple props is really not ideal.
	// We should use data.data
	export let data;
	export let urlModel: string; // Equivalent of data.urlModel
	export let fields: string[] | null = null;
	fields ??= Object.keys(data);
	export let exclude: string[] = [];
	export let cssClasses: string = '';
	let currentLocale = 'en';

	onMount(() => {
		currentLocale = getCookie('PARAGLIDE_LOCALE') ?? 'en';
	});

	/* if (!data.urlModel) {
    data.urlModel = data.URLModel; // Fix this
  } */

	function truncateString(str: string, maxLength: number = 50): string {
		return str.length > maxLength ? str.slice(0, maxLength) + '...' : str;
	}
</script>

<dl
	class="-my-3 divide-y divide-gray-100 text-sm border border-gray-100 {cssClasses}"
	data-testid="description-list"
>
	{#each fields
		.filter((key) => !exclude.includes(key))
		.map((key) => [key, data[key]]) as [key, value]}
		<div
			class="grid grid-cols-1 gap-1 py-3 px-2 even:bg-gray-50 sm:grid-cols-3 sm:gap-4"
			data-testid="description-list-row-elem"
		>
			<dt class="font-medium text-gray-900" data-testid="{key.replace('_', '-')}-field-title">
				<!-- This data-testid must have a "dyn-" prefix. -->
				{safeTranslate(key)}
			</dt>
			<dd class="text-gray-700 sm:col-span-2">
				<ul>
					<li
						class="list-none"
						data-testid={!(value instanceof Array) ? key.replace('_', '-') + '-field-value' : null}
					>
						{#if value !== null && value !== undefined && value !== ''}
							{#if key === 'library'}
								{@const itemHref = `/loaded-libraries/${value.id}`}
								<Anchor breadcrumbAction="push" href={itemHref} class="anchor">{value.name}</Anchor>
							{:else if key === 'severity' && urlModel !== 'incidents'}
								<!-- We must add translations for the following severity levels -->
								<!-- Is this a correct way to convert the severity integer to the stringified security level ? -->
								{@const stringifiedSeverity =
									value < 0
										? '--'
										: (safeTranslate(['low', 'medium', 'high', 'critical'][value]) ??
											m.undefined())}
								{stringifiedSeverity}
							{:else if key === 'children_assets'}
								{#if Object.keys(value).length > 0}
									<ul class="inline-flex flex-wrap space-x-4">
										{#each value as val}
											<li data-testid={key.replace('_', '-') + '-field-value'}>
												{#if val.str && val.id}
													{@const itemHref = `/${
														URL_MODEL_MAP[urlModel]['foreignKeyFields']?.find(
															(item) => item.field === key
														)?.urlModel
													}/${val.id}`}
													<Anchor breadcrumbAction="push" href={itemHref} class="anchor">
														{truncateString(val.str)}</Anchor
													>
												{:else if val.str}
													{safeTranslate(val.str)}
												{:else}
													{value}
												{/if}
											</li>
										{/each}
									</ul>
								{:else}
									--
								{/if}
							{:else if Array.isArray(value)}
								{#if Object.keys(value).length > 0}
									<ul>
										{#each value as val}
											<li data-testid={key.replace('_', '-') + '-field-value'}>
												{#if val.str && val.id}
													{@const itemHref = `/${
														URL_MODEL_MAP[urlModel]['foreignKeyFields']?.find(
															(item) => item.field === key
														)?.urlModel
													}/${val.id}`}
													<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
														>{val.str}</Anchor
													>
												{:else if val.str}
													{safeTranslate(val.str)}
												{:else}
													{value}
												{/if}
											</li>
										{/each}
									</ul>
								{:else}
									--
								{/if}
							{:else if value.id && !value.hexcolor}
								{@const itemHref = `/${
									URL_MODEL_MAP[urlModel]['foreignKeyFields']?.find((item) => item.field === key)
										?.urlModel
								}/${value.id}`}
								{#if key === 'ro_to_couple'}
									<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
										>{safeTranslate(toCamelCase(value.str.split(' - ')[0]))} - {value.str.split(
											'-'
										)[1]}</Anchor
									>
								{:else}
									<Anchor breadcrumbAction="push" href={itemHref} class="anchor">{value.str}</Anchor
									>
								{/if}
								<!-- Shortcut before DetailView refactoring -->
							{:else if value === 'P1'}
								<li class="fa-solid fa-flag text-red-500"></li>
								{m.p1()}
							{:else if value === 'P2'}
								<li class="fa-solid fa-flag text-orange-500"></li>
								{m.p2()}
							{:else if value === 'P3'}
								<li class="fa-solid fa-flag text-blue-500"></li>
								{m.p3()}
							{:else if value === 'P4'}
								<li class="fa-solid fa-flag text-gray-500"></li>
								{m.p4()}
							{:else if isURL(value) && !value.startsWith('urn')}
								<Anchor breadcrumbAction="push" href={value} target="_blank" class="anchor"
									>{value}</Anchor
								>
							{:else if ISO_8601_REGEX.test(value) && (key === 'created_at' || key === 'updated_at' || key === 'expiry_date' || key === 'accepted_at' || key === 'rejected_at' || key === 'revoked_at' || key === 'eta' || key === 'expiration_date')}
								{formatDateOrDateTime(value, currentLocale)}
							{:else if m[toCamelCase(value.str || value.name)]}
								{safeTranslate((value.str || value.name) ?? value)}
							{:else}
								{(value.str || value.name) ?? value}
							{/if}
						{:else}
							--
						{/if}
					</li>
				</ul>
			</dd>
		</div>
	{/each}
</dl>
