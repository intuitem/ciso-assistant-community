<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		assessable: boolean;
		result: string | undefined;
		resultColor: string;
		isAssigned: boolean;
		assignmentInfo: { actorName: string } | null;
	}

	let { assessable, result, resultColor, isAssigned, assignmentInfo }: Props = $props();
</script>

<div class="flex items-center gap-2 min-w-[80px]">
	{#if assessable}
		<!-- Result badge -->
		{#if result}
			<span
				class="px-2 py-0.5 rounded text-xs font-medium"
				style="background-color: {resultColor}20; color: {resultColor};"
			>
				{safeTranslate(result)}
			</span>
		{/if}
	{:else}
		<!-- Section indicator -->
		<span class="text-gray-400">
			<i class="fa-solid fa-folder text-xs"></i>
		</span>
	{/if}
</div>
