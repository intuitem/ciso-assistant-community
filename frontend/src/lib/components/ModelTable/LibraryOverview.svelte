<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Props {
		cell: Array<any>;
		[key: string]: any;
	}

	type ReferentialObject =
		| 'reference_controls'
		| 'threats'
		| 'framework'
		| 'risk_matrix'
		| 'requirement_mapping_set';

	let { cell, ...rest }: Props = $props();
	let display = $derived(Object.entries(cell));

	function getLocalizedOverview(objectType: ReferentialObject, count: number) {
		return m.libraryOverview({ objectType: safeTranslate(objectType), count });
	}
</script>

<ul class="list-disc" {...rest}>
	{#each display as obj}
		<li>{getLocalizedOverview(obj[0] as ReferentialObject, obj[1])}</li>
	{/each}
</ul>
