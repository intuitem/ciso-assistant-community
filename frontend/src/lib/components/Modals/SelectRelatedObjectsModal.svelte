<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	export let parentModel: any;
	export let parentObject: any;
	export let relatedModel: any;
	export let relatedUrlModel: string;
	export let relationField: string;
	export let listEndpoint: string;
	export let initialSelectedIds: string[] = [];

	let loading = true;
	let error: string | null = null;
	let items: any[] = [];
	let selectedIds = new Set<string>(initialSelectedIds);

	let saving = false;
	let saveError: string | null = null;

	onMount(async () => {
		try {
			const url = new URL(listEndpoint, window.location.origin);
			// Tu peux adapter limite/tri ici
			url.searchParams.set('limit', '100');

			const response = await fetch(url.toString());
			if (!response.ok) throw new Error(`Failed to load ${relatedUrlModel} list`);

			const payload = await response.json();

			// On essaie d'être un peu souple : DRF-style (results) ou body direct
			items = payload.results ?? payload.body ?? payload ?? [];
		} catch (e: any) {
			console.error(e);
			error = e?.message ?? 'Unable to load selectable objects';
		} finally {
			loading = false;
		}
	});

	function toggle(id: string) {
		if (selectedIds.has(id)) {
			selectedIds.delete(id);
		} else {
			selectedIds.add(id);
		}
		// forcer la réactivité
		selectedIds = new Set(selectedIds);
	}

    async function saveSelection() {
        saveError = null;
        saving = true;
        try {
            // On imite un <form method="POST" action="?/update">
            const url = `/${parentModel.urlModel}/${parentObject.id}?/update`;

            const formData = new FormData();
            // Multiple valeurs comme un <select multiple name="relationField">
            for (const id of Array.from(selectedIds)) {
                formData.append(relationField, id);
            }

            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`Failed to save selection (${response.status})`);
            }

            window.location.reload();
        } catch (e: any) {
            console.error(e);
            saveError = e?.message ?? 'Unable to save selection';
        } finally {
            saving = false;
        }
    }
</script>

<div
	class="card bg-white shadow-lg rounded-container p-4
           flex flex-col gap-4 min-w-[320px] max-w-[640px]"
>

	{#if loading}
		<p class="text-sm text-gray-500">{m.loading()}</p>
	{:else if error}
		<p class="text-sm text-red-600">{error}</p>
	{:else}
		<p class="text-sm text-gray-600">
			{safeTranslate('select-' + relatedModel.info.localNamePlural)}
		</p>

		<div class="max-h-80 overflow-y-auto border rounded-md divide-y">
			{#if items.length === 0}
				<p class="text-sm text-gray-400 p-3">{m.noDataAvailable()}</p>
			{:else}
				{#each items as item}
					{@const id = item.id}
					{@const label = item.str ?? item.name ?? item.reference ?? id}
					<label class="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-gray-50">
						<input
							type="checkbox"
							class="checkbox checkbox-sm"
							checked={selectedIds.has(id)}
							on:change={() => toggle(id)}
						/>
						<span class="text-sm text-gray-800 truncate">{label}</span>
					</label>
				{/each}
			{/if}
		</div>

		{#if saveError}
			<p class="text-sm text-red-600">{saveError}</p>
		{/if}

		<div class="flex justify-end gap-2">
			<!-- Le wrapper de modale gère normalement la fermeture via un bouton "Annuler" global.
			     Si tu veux un bouton Annuler ici, tu peux émettre un event ou utiliser modalStore. -->
			<button
				class="btn preset-filled-primary-500"
				type="button"
				on:click={saveSelection}
				disabled={saving}
			>
				{#if saving}
					<i class="fa-solid fa-spinner fa-spin mr-2"></i>
				{/if}
				{m.save()}
			</button>
		</div>
	{/if}
</div>
