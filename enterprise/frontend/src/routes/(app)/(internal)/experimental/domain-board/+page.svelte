<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import DomainBoard from './DomainBoard.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	$pageTitle = 'Domain whiteboard';
</script>

<div class="flex h-[calc(100vh-9rem)] flex-col">
	<div class="mb-3 flex items-center gap-3 rounded-base bg-surface-50-950 p-3 shadow-sm">
		<h4 class="font-bold text-surface-800-200">
			<i class="fa-solid fa-sitemap mr-2"></i>Domain whiteboard
		</h4>
		<span
			class="rounded border border-surface-200-800 bg-surface-100-900 px-2 py-0.5 text-xs text-surface-500"
		>
			experimental
		</span>
	</div>

	<div class="min-h-0 flex-1">
		<!-- Both: without the receiving tree every domain reads as unable to accept
		     children, which renders a board that rejects every move. -->
		{#if data.movableTree && data.receivingTree}
			<DomainBoard
				movableTree={data.movableTree}
				receivingTree={data.receivingTree}
				folderModel={data.folderModel}
			/>
		{:else}
			<div
				class="flex h-full items-center justify-center rounded-base border border-dashed border-surface-300-700 bg-surface-50-950 text-surface-500"
			>
				<div class="text-center">
					<i class="fa-solid fa-sitemap mb-3 text-4xl text-surface-300"></i>
					<p class="text-sm">The domain tree could not be loaded.</p>
				</div>
			</div>
		{/if}
	</div>
</div>
