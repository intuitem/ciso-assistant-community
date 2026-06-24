<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();

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

<div class="space-y-8">
	<!-- My portals -->
	<section class="card bg-surface-50-950 p-6 space-y-4">
		<div class="flex items-center justify-between">
			<h2 class="text-lg font-bold">{m.portals()}</h2>
			<form method="POST" action="?/createPortal" use:enhance class="flex items-center gap-2">
				<input name="name" placeholder={m.name()} required class="input rounded-md text-sm" />
				<button class="btn preset-filled-primary-500 btn-sm">
					<i class="fa-solid fa-plus mr-1"></i>{m.add()}
				</button>
			</form>
		</div>
		<div class="divide-y divide-surface-200-800">
			{#each data.portals as p}
				<div class="flex items-center justify-between py-2">
					<div class="flex items-center gap-3">
						<i class="fa-solid fa-grip text-surface-400"></i>
						<a href="/portal-editor/{p.id}" class="font-medium hover:text-primary-500">{p.name}</a>
						<a href="/portal/{p.id}" class="text-xs text-primary-500" aria-label="Open portal"
							><i class="fa-solid fa-arrow-up-right-from-square"></i></a
						>
						<span
							class="text-[10px] uppercase rounded-full px-2 py-0.5 {p.status === 'published'
								? 'bg-success-500/15 text-success-700'
								: 'bg-surface-200-800 text-surface-500'}">{p.status}</span
						>
						{#if p.is_default}<span class="text-[10px] uppercase text-surface-400">default</span
							>{/if}
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
			{:else}
				<p class="py-2 text-sm text-surface-500">
					No portals yet — create one or start from a preset below.
				</p>
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
