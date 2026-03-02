<script lang="ts">
	import { NodeResizer } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		id: string;
		data: {
			key: string;
			icon: string;
			twBg: string;
			twBorder: string;
			twText: string;
			stage: number;
		};
	}

	let { id, data }: Props = $props();

	const editor = getContext<{ dragOverStage: number | null; readonly: boolean }>('killChainEditor');
	const isHighlighted = $derived(editor?.dragOverStage === data.stage);
</script>

{#if !editor?.readonly}
	<NodeResizer minWidth={220} minHeight={300} />
{/if}

<div
	class="w-full h-full rounded-xl transition-all duration-200 overflow-hidden border-2 border-dashed {data.twBorder} {data.twBg}"
	class:opacity-70={!isHighlighted}
>
	<div class="flex items-center justify-center gap-2 py-3 {data.twBg}">
		<i class="fa-solid {data.icon} {data.twText}"></i>
		<span class="text-xs font-semibold {data.twText}">
			{safeTranslate(data.key)}
		</span>
	</div>
</div>
