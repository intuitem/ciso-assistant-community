<script lang="ts">
	import { URL_MODEL_MAP, type ModelMapEntry } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Props {
		cell: Array<any>;
		[key: string]: any;
	}

	type Operation = 'add' | 'view' | 'change' | 'delete';

	let { cell, ...rest }: Props = $props();
	let display = $derived(cell as string[]);

	function getLocalizedPermission(operation: Operation, model: string) {
		return m.permissionDisplay({ operation: safeTranslate(operation), model });
	}

	function getModelLocalizedName(name: string) {
		return safeTranslate(
			Object.values(URL_MODEL_MAP).filter((m: ModelMapEntry) => m.name === name)[0]?.localName ??
				name
		);
	}
</script>

<ul class="list-disc" {...rest}>
	{#each display as obj}
		{@const permission = obj.split('_')}
		<li>
			{getLocalizedPermission(permission[0] as Operation, getModelLocalizedName(permission[1]))}
		</li>
	{/each}
</ul>
