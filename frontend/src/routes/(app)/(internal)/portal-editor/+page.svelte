<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();

	const internalPortals = $derived((data.portals ?? []).filter((p: any) => !p.is_public));
	const publicPortals = $derived((data.portals ?? []).filter((p: any) => p.is_public));

	let creating = $state<null | 'internal' | 'public'>(null);
	let newName = $state('');

	function openCreate(type: 'internal' | 'public') {
		newName = '';
		creating = type;
	}

	function confirmDelete(e: MouseEvent, name: string) {
		const form = (e.currentTarget as HTMLElement).closest('form') as HTMLFormElement;
		const modal: ModalSettings = {
			type: 'confirm',
			title: m.delete(),
			body: m.deleteModalMessage({ name }),
			buttonTextConfirm: m.delete(),
			response: (confirmed: boolean) => {
				if (confirmed) form.requestSubmit();
			}
		};
		modalStore.trigger(modal);
	}
</script>

{#snippet portalRow(p: any)}
	<div class="flex items-center justify-between py-2">
		<div class="flex items-center gap-3">
			<i class="fa-solid fa-window-maximize text-surface-400"></i>
			<a href="/portal-editor/{p.id}" class="font-medium hover:text-primary-500">{p.name}</a>
			{#if p.status === 'published'}
				<a
					href={p.is_public ? `/trust/${p.public_token}` : `/portal/${p.id}`}
					target={p.is_public ? '_blank' : undefined}
					rel={p.is_public ? 'noopener' : undefined}
					class="text-xs text-primary-500"
					aria-label={m.open()}><i class="fa-solid fa-arrow-up-right-from-square"></i></a
				>
			{/if}
			<span
				class="text-[10px] uppercase rounded-full px-2 py-0.5 {p.status === 'published'
					? 'bg-success-500/15 text-success-700'
					: 'bg-surface-200-800 text-surface-500'}">{p.status}</span
			>
			{#if p.is_default}<span class="text-[10px] uppercase text-surface-400">default</span>{/if}
		</div>
		<div class="flex items-center gap-2">
			<a href="/portal-editor/{p.id}" class="btn btn-sm preset-tonal">{m.edit()}</a>
			<form method="POST" action="?/deletePortal" use:enhance>
				<input type="hidden" name="id" value={p.id} />
				<button
					type="button"
					onclick={(e) => confirmDelete(e, p.name)}
					class="btn btn-sm preset-tonal-error"
					aria-label={m.delete()}
					title={m.delete()}
				>
					<i class="fa-solid fa-trash"></i>
				</button>
			</form>
		</div>
	</div>
{/snippet}

<div class="space-y-8">
	<!-- Internal portals -->
	<section class="card bg-surface-50-950 p-6 space-y-4">
		<div class="flex items-center justify-between">
			<h2 class="text-lg font-bold">
				<i class="fa-solid fa-table-cells-large mr-1 text-surface-400"></i>{m.internalPortals()}
			</h2>
			<button onclick={() => openCreate('internal')} class="btn btn-sm preset-filled-primary-500">
				<i class="fa-solid fa-plus mr-1"></i>{m.add()}
			</button>
		</div>
		<div class="divide-y divide-surface-200-800">
			{#each internalPortals as p}
				{@render portalRow(p)}
			{:else}
				<p class="py-2 text-sm text-surface-500">{m.noInternalPortals()}</p>
			{/each}
		</div>
	</section>

	<!-- Public portals (trust center) -->
	<section class="card bg-surface-50-950 p-6 space-y-4">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<h2 class="text-lg font-bold">
				<i class="fa-solid fa-globe mr-1 text-violet-500"></i>{m.publicPortals()}
			</h2>
			<div class="flex flex-wrap gap-2">
				<a href="/portal-editor/snapshots" class="btn btn-sm preset-tonal">
					<i class="fa-solid fa-chart-pie mr-1"></i>{m.frameworkSnapshots()}
				</a>
				<a href="/portal-editor/documents" class="btn btn-sm preset-tonal">
					<i class="fa-solid fa-folder-open mr-1"></i>{m.publicDocuments()}
				</a>
				<button onclick={() => openCreate('public')} class="btn btn-sm preset-filled-primary-500">
					<i class="fa-solid fa-plus mr-1"></i>{m.add()}
				</button>
			</div>
		</div>
		<p class="text-sm text-surface-500">{m.publicPortalsHelp()}</p>
		<div class="divide-y divide-surface-200-800">
			{#each publicPortals as p}
				{@render portalRow(p)}
			{:else}
				<p class="py-2 text-sm text-surface-500">{m.noPublicPortals()}</p>
			{/each}
		</div>
	</section>

	<!-- Preset gallery -->
	<section class="card bg-surface-50-950 p-6 space-y-4">
		<h2 class="text-lg font-bold">{m.portalPresetGallery()}</h2>
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
			{#each data.presets as preset}
				<div class="flex flex-col rounded-xl border border-surface-200-800 p-4">
					<div class="flex items-center gap-2">
						<i class="fa-solid fa-layer-group text-violet-500"></i>
						<span class="font-semibold">{preset.name}</span>
						{#if !preset.is_user_authored}
							<span class="text-[10px] text-surface-400"
								><i class="fa-solid fa-lock"></i> library</span
							>
						{/if}
					</div>
					{#if preset.description}
						<p class="mt-1 text-xs text-surface-600-400">{preset.description}</p>
					{/if}
					<form method="POST" action="?/usePreset" use:enhance class="mt-3">
						<input type="hidden" name="preset" value={preset.id} />
						<button class="btn btn-sm preset-filled-primary-500 w-full">
							<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{m.useThisPreset()}
						</button>
					</form>
				</div>
			{:else}
				<p class="text-sm text-surface-500">No presets available yet.</p>
			{/each}
		</div>
	</section>
</div>

{#if creating}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget) creating = null;
		}}
	>
		<div class="w-full max-w-md rounded-2xl bg-surface-50-950 p-6 shadow-xl space-y-4">
			<h2 class="text-lg font-bold">
				{creating === 'public' ? m.newPublicPortal() : m.newInternalPortal()}
			</h2>
			<form method="POST" action="?/createPortal" use:enhance class="space-y-3">
				<input type="hidden" name="visibility" value={creating} />
				<label class="block text-sm">
					<span class="block text-surface-600-400">{m.name()}</span>
					<!-- svelte-ignore a11y_autofocus -->
					<input
						name="name"
						bind:value={newName}
						required
						autofocus
						class="input w-full rounded-md"
					/>
				</label>
				<div class="flex justify-end gap-2">
					<button type="button" onclick={() => (creating = null)} class="btn btn-sm preset-tonal"
						>{m.cancel()}</button
					>
					<button class="btn btn-sm preset-filled-primary-500">{m.create()}</button>
				</div>
			</form>
		</div>
	</div>
{/if}
