<script lang="ts">
	import FlippableCard from './FlippableCard.svelte';
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Group entity assessments by folder
	const groupByFolder = (assessments: any[]) => {
		if (!assessments || assessments.length === 0) return [];

		const grouped = new Map<
			string,
			{ folder_id: string; folder_name: string; assessments: any[] }
		>();

		assessments.forEach((assessment) => {
			const folderId = assessment.folder_id || 'no-folder';
			const folderName = assessment.folder_name || 'No Domain';

			if (!grouped.has(folderId)) {
				grouped.set(folderId, {
					folder_id: folderId,
					folder_name: folderName,
					assessments: []
				});
			}
			grouped.get(folderId)!.assessments.push(assessment);
		});

		return Array.from(grouped.values());
	};

	const groupedData = $derived(groupByFolder(data.data));
</script>

{#if groupedData && groupedData.length > 0}
	<div class="p-6 bg-white bg-opacity-95 space-y-8">
		{#each groupedData as group}
			<div>
				<div class="flex items-center gap-3 mb-4">
					{#if group.folder_id && group.folder_id !== 'no-folder'}
						<a
							href="/folders/{group.folder_id}"
							class="text-xl font-bold text-gray-800 hover:text-primary-600 hover:underline"
						>
							{group.folder_name}
						</a>
					{:else}
						<span class="text-xl font-bold text-gray-800">{group.folder_name}</span>
					{/if}
					<span class="badge preset-tonal-secondary">{group.assessments.length}</span>
				</div>
				<div
					class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
					role="list"
					data-testid="cards-list"
				>
					{#each group.assessments as entity_assessment}
						<FlippableCard {entity_assessment} />
					{/each}
				</div>
			</div>
		{/each}
	</div>
{:else}
	<div class="p-4" data-testid="no-data-available">{m.noDataAvailable()}</div>
{/if}
