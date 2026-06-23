<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getToastStore } from '$lib/components/Toast/stores';
	import IconPicker from '$lib/components/IconPicker/IconPicker.svelte';
	import PortalGrid from '$lib/components/PortalGrid/PortalGrid.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const toast = getToastStore();
	let preview = $state(false);

	type Item = {
		icon: string;
		title: string;
		description: string;
		kind: 'create' | 'navigate' | 'external' | 'status';
		target: Record<string, string>;
	};
	type Section = { title: string; description: string; items: Item[] };

	let sections = $state<Section[]>(
		((data.portal.content?.sections ?? []) as any[]).map((s) => ({
			title: s.title ?? '',
			description: s.description ?? '',
			items: (s.items ?? []).map((i: any) => ({
				icon: i.icon ?? '',
				title: i.title ?? '',
				description: i.description ?? '',
				kind: i.kind ?? 'navigate',
				target: i.target ?? {}
			}))
		}))
	);

	const KINDS = ['create', 'navigate', 'external', 'status'] as const;

	const payload = $derived(JSON.stringify({ sections }));

	function addSection() {
		sections.push({ title: 'New group', description: '', items: [] });
	}
	function removeSection(i: number) {
		sections.splice(i, 1);
	}
	function moveSection(i: number, dir: -1 | 1) {
		const j = i + dir;
		if (j < 0 || j >= sections.length) return;
		[sections[i], sections[j]] = [sections[j], sections[i]];
	}
	function addItem(si: number) {
		sections[si].items.push({
			icon: 'fa-star',
			title: 'New item',
			description: '',
			kind: 'navigate',
			target: {}
		});
	}
	function removeItem(si: number, ii: number) {
		sections[si].items.splice(ii, 1);
	}
	function moveItem(si: number, ii: number, dir: -1 | 1) {
		const items = sections[si].items;
		const j = ii + dir;
		if (j < 0 || j >= items.length) return;
		[items[ii], items[j]] = [items[j], items[ii]];
	}
	function moveItemToGroup(si: number, ii: number, targetSi: number) {
		if (targetSi === si) return;
		const [item] = sections[si].items.splice(ii, 1);
		sections[targetSi].items.push(item);
	}

	function targetField(kind: Item['kind']) {
		if (kind === 'create') return { key: 'model', label: 'Model (url name)', ph: 'incidents' };
		if (kind === 'status') return { key: 'source', label: 'Source key', ph: 'iso-27001' };
		return { key: 'url', label: 'URL', ph: kind === 'external' ? 'https://…' : '/incidents' };
	}
</script>

<div class="space-y-6 pb-28">
	<div class="flex items-center gap-3">
		<a href="/portal-editor" class="text-surface-500 hover:text-primary-500">
			<i class="fa-solid fa-arrow-left"></i>
		</a>
		<form method="POST" action="?/updateMeta" use:enhance class="flex items-center gap-2 grow">
			<input
				name="name"
				value={data.portal.name}
				class="input rounded-md text-lg font-bold max-w-md"
			/>
			<button class="btn btn-sm preset-tonal">{m.save()}</button>
		</form>
		<a href="/portal/{data.portal.id}" class="text-xs text-primary-500" aria-label="Open portal"
			><i class="fa-solid fa-arrow-up-right-from-square"></i></a
		>
		<span
			class="text-[10px] uppercase rounded-full px-2 py-0.5 {data.portal.status === 'published'
				? 'bg-success-500/15 text-success-700'
				: 'bg-surface-200-800 text-surface-500'}">{data.portal.status}</span
		>
		<button class="btn btn-sm preset-tonal" onclick={() => (preview = !preview)}>
			<i class="fa-solid {preview ? 'fa-pen' : 'fa-eye'} mr-1"></i>{preview
				? m.edit()
				: m.preview()}
		</button>
		<form method="POST" action="?/duplicate" use:enhance>
			<button class="btn btn-sm preset-tonal" aria-label={m.duplicate()} title={m.duplicate()}
				><i class="fa-solid fa-copy"></i></button
			>
		</form>
	</div>

	{#if !preview}
		{#each sections as section, si}
			<section class="card bg-surface-50-950 p-5 space-y-4">
				<div class="flex items-center gap-2">
					<i class="fa-solid fa-layer-group text-surface-400"></i>
					<input
						bind:value={section.title}
						placeholder="Group title"
						class="input rounded-md font-semibold grow"
					/>
					<button
						onclick={() => moveSection(si, -1)}
						class="btn-icon btn-sm preset-tonal"
						aria-label="Move group up"><i class="fa-solid fa-chevron-up"></i></button
					>
					<button
						onclick={() => moveSection(si, 1)}
						class="btn-icon btn-sm preset-tonal"
						aria-label="Move group down"><i class="fa-solid fa-chevron-down"></i></button
					>
					<button
						onclick={() => removeSection(si)}
						class="btn-icon btn-sm preset-tonal-error"
						aria-label={m.delete()}
						title={m.delete()}><i class="fa-solid fa-trash"></i></button
					>
				</div>

				<div class="space-y-3 pl-6">
					{#each section.items as item, ii}
						{@const tf = targetField(item.kind)}
						<div
							class="flex flex-wrap items-end gap-2 rounded-lg border border-surface-200-800 p-3"
						>
							<label class="text-[10px] text-surface-500">
								<span class="block">Icon</span>
								<IconPicker bind:value={item.icon} />
							</label>
							<label class="text-[10px] text-surface-500 grow">
								<span class="block">{m.title()}</span>
								<input bind:value={item.title} class="input rounded-md text-sm" />
							</label>
							<label class="text-[10px] text-surface-500">
								<span class="block">Kind</span>
								<select bind:value={item.kind} class="select rounded-md text-sm">
									{#each KINDS as k}<option value={k}>{k}</option>{/each}
								</select>
							</label>
							<label class="text-[10px] text-surface-500 grow">
								<span class="block">{tf.label}</span>
								<input
									bind:value={item.target[tf.key]}
									placeholder={tf.ph}
									class="input rounded-md text-sm"
								/>
							</label>
							<label class="text-[10px] text-surface-500">
								<span class="block">Group</span>
								<select
									value={si}
									onchange={(e) => moveItemToGroup(si, ii, +e.currentTarget.value)}
									class="select rounded-md text-sm"
								>
									{#each sections as s, gi}<option value={gi}>{s.title || `Group ${gi + 1}`}</option
										>{/each}
								</select>
							</label>
							<label class="text-[10px] text-surface-500 w-full">
								<span class="block">Description (markdown)</span>
								<textarea
									bind:value={item.description}
									rows="2"
									class="textarea rounded-md text-sm w-full"
								></textarea>
							</label>
							<div class="flex gap-1">
								<button
									onclick={() => moveItem(si, ii, -1)}
									class="btn-icon btn-sm preset-tonal"
									aria-label="Move item up"><i class="fa-solid fa-chevron-up"></i></button
								>
								<button
									onclick={() => moveItem(si, ii, 1)}
									class="btn-icon btn-sm preset-tonal"
									aria-label="Move item down"><i class="fa-solid fa-chevron-down"></i></button
								>
								<button
									onclick={() => removeItem(si, ii)}
									class="btn-icon btn-sm preset-tonal-error"
									aria-label={m.delete()}><i class="fa-solid fa-trash"></i></button
								>
							</div>
						</div>
					{/each}
					<button onclick={() => addItem(si)} class="btn btn-sm preset-tonal">
						<i class="fa-solid fa-plus mr-1"></i>{m.addItem()}
					</button>
				</div>
			</section>
		{/each}

		<button onclick={addSection} class="btn preset-tonal">
			<i class="fa-solid fa-plus mr-1"></i>{m.addGroup()}
		</button>
	{:else}
		<div class="rounded-2xl bg-linear-to-br from-surface-100-900 to-surface-200-800 p-8">
			<PortalGrid {sections} />
		</div>
	{/if}
</div>

<div
	class="fixed bottom-0 right-0 left-64 flex items-center justify-end gap-3 border-t border-surface-200-800 bg-surface-50-950/90 px-8 py-3 backdrop-blur"
>
	<form
		method="POST"
		action="?/setStatus"
		use:enhance={() =>
			async ({ result, update }) => {
				await update();
				if (result.type === 'success')
					toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
			}}
	>
		<input
			type="hidden"
			name="status"
			value={data.portal.status === 'published' ? 'draft' : 'published'}
		/>
		<button class="btn preset-tonal">
			{data.portal.status === 'published' ? m.unpublish() : m.publish()}
		</button>
	</form>
	<form
		method="POST"
		action="?/saveContent"
		use:enhance={() =>
			async ({ result, update }) => {
				await update({ reset: false });
				if (result.type === 'success')
					toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
			}}
	>
		<input type="hidden" name="payload" value={payload} />
		<button class="btn preset-filled-primary-500">
			<i class="fa-solid fa-floppy-disk mr-1"></i>{m.save()}
		</button>
	</form>
</div>
