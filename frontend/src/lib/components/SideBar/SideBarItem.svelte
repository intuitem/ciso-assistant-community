<script lang="ts">
	import { page } from '$app/stores';
	import type { ModalSettings } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';
	import * as m from '$paraglide/messages';

	export let item: any; // TODO: type this

	const modalStore = getModalStore();

	$: classesActive = (href: string) =>
		href === $page.url.pathname
			? 'bg-primary-100 text-primary-800'
			: 'hover:bg-primary-50 text-gray-800 ';

	async function onClickScoringAssistant(event) {
		const req = await fetch(`/risk-matrices`);
		const risk_matrices = await req.json();

		if (risk_matrices.length === 0) {
			const modal: ModalSettings = {
				type: 'component',
				component: 'displayJSONModal',
				title: m.scoringAssistantNoMatrixError(),
				body: JSON.stringify({})
			};
			modalStore.trigger(modal);
		} else {
			const clickEvent = new MouseEvent('click', {
				bubbles: true,
				cancelable: false
			});
			event.target.dispatchEvent(clickEvent);
		}
	}

	function onClick(event,item) {
		if (item.name === "scoringAssistant") {
			if (!event.cancelable) { return; }
			event.preventDefault();
			return onClickScoringAssistant(event);
		}
	}
</script>

{#each item as item}
	<a
		href={item.href}
		class="unstyled flex whitespace-nowrap items-center py-2 text-sm font-normal rounded-token {classesActive(
			item.href ?? ''
		)}"
		data-testid={'accordion-item-' + item.href.substring(1)}
		on:click={(event) => onClick(event,item)}
	>
		<span class="px-4 flex items-center w-full space-x-2 text-xs">
			<i class="{item.fa_icon} w-1/12" />
			<span class="text-sm tracking-wide truncate">{localItems(languageTag())[item.name]}</span>
		</span></a
	>
{/each}
