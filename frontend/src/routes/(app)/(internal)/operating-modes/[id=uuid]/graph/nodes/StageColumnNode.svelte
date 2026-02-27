<script lang="ts">
	import { NodeResizer } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		id: string;
		data: {
			key: string;
			icon: string;
			bg: string;
			border: string;
			stage: number;
		};
	}

	let { id, data }: Props = $props();

	const editor = getContext<{ dragOverStage: number | null }>('killChainEditor');
	const isHighlighted = $derived(editor?.dragOverStage === data.stage);
</script>

<NodeResizer
	minWidth={220}
	minHeight={300}
	color={data.border}
	lineStyle="border-style: dashed;"
/>

<div
	class="w-full h-full rounded-xl transition-all duration-200 overflow-hidden"
	style="
		background: {isHighlighted ? data.bg : data.bg + '99'};
		border: 2px dashed {data.border};
		opacity: {isHighlighted ? 1 : 0.7};
	"
>
	<div
		class="flex items-center justify-center gap-2 py-3"
		style="background: {data.border}22;"
	>
		<i class="fa-solid {data.icon}" style="color: {data.border};"></i>
		<span class="text-xs font-semibold" style="color: {data.border};">
			{safeTranslate(data.key)}
		</span>
	</div>
</div>
