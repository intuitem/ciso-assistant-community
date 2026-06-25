<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getToastStore } from '$lib/components/Toast/stores';
	import IconPicker from '$lib/components/IconPicker/IconPicker.svelte';
	import PortalGrid from '$lib/components/PortalGrid/PortalGrid.svelte';
	import { SCAFFOLDABLE_MODELS } from '$lib/utils/modelTargets';
	import { urlParamModelVerboseName } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { superForm } from 'sveltekit-superforms';
	import { page } from '$app/state';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import type { PageData } from './$types';

	const personalFoldersMisconfigured = $derived(
		!!page.data?.featureflags?.personal_folders && !page.data?.settings?.personal_folders_parent
	);

	const modelOptions = SCAFFOLDABLE_MODELS.map((model) => ({
		value: model,
		label: safeTranslate(urlParamModelVerboseName(model))
	})).sort((a, b) => a.label.localeCompare(b.label));

	let { data }: { data: PageData } = $props();
	const toast = getToastStore();
	let view = $state<'edit' | 'preview' | 'settings'>('edit');

	const settingsSuperform = superForm(data.settingsForm, {
		dataType: 'json',
		resetForm: false,
		invalidateAll: true,
		onUpdated: ({ form }) => {
			if (form.valid)
				toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
		}
	});
	const { form: settingsData, enhance: settingsEnhance } = settingsSuperform;

	const regenEnhance =
		() =>
		async ({ result, update }: { result: { type: string }; update: () => Promise<void> }) => {
			await update();
			if (result.type === 'success')
				toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
		};

	type Item = {
		icon: string;
		title: string;
		description: string;
		kind:
			| 'create'
			| 'navigate'
			| 'external'
			| 'status'
			| 'metric'
			| 'badge'
			| 'document'
			| 'framework';
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

	const KINDS = [
		'create',
		'navigate',
		'external',
		'status',
		'metric',
		'badge',
		'document',
		'framework'
	] as const;
	// Kinds surfaced on the unauthenticated trust-center page (mirror of backend PUBLIC_SAFE_TILE_KINDS).
	const PUBLIC_SAFE = ['external', 'status', 'metric', 'badge', 'document', 'framework'];

	const METRIC_SOURCES = [
		{ value: '', label: m.manual() },
		{ value: 'frameworks_count', label: m.frameworksMonitored() },
		{ value: 'controls_count', label: m.controlsCovered() }
	];

	const payload = $derived(JSON.stringify({ sections }));

	// Preview enrichment: graft the captured snapshot onto framework tiles so the
	// preview shows real donuts (the live /trust page is enriched server-side).
	const snapById = $derived(new Map((data.snapshots ?? []).map((s: any) => [s.id, s])));
	const previewSections = $derived(
		sections.map((sec) => ({
			...sec,
			items: sec.items.map((it) => {
				if (it.kind === 'framework' && it.target.snapshot) {
					const s: any = snapById.get(it.target.snapshot);
					if (s)
						return {
							...it,
							snapshot: {
								name: s.name,
								framework_name: s.framework_name,
								summary: s.summary,
								token: s.public_token
							}
						};
				}
				return it;
			})
		}))
	);

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
		if (kind === 'metric') return { key: 'value', label: m.value(), ph: '128' };
		if (kind === 'badge') return { key: 'image_url', label: m.logoUrl(), ph: 'https://…' };
		if (kind === 'document') return { key: 'token', label: m.document(), ph: '' };
		if (kind === 'framework') return { key: 'snapshot', label: m.framework(), ph: '' };
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
		<button
			class="btn btn-sm {view === 'settings' ? 'preset-filled-primary-500' : 'preset-tonal'}"
			onclick={() => (view = view === 'settings' ? 'edit' : 'settings')}
		>
			<i class="fa-solid fa-sliders mr-1"></i>{m.settings()}
		</button>
		<button
			class="btn btn-sm preset-tonal"
			onclick={() => (view = view === 'preview' ? 'edit' : 'preview')}
		>
			<i class="fa-solid {view === 'preview' ? 'fa-pen' : 'fa-eye'} mr-1"></i>{view === 'preview'
				? m.edit()
				: m.preview()}
		</button>
		<form method="POST" action="?/duplicate" use:enhance>
			<button class="btn btn-sm preset-tonal" aria-label={m.duplicate()} title={m.duplicate()}
				><i class="fa-solid fa-copy"></i></button
			>
		</form>
	</div>

	{#if personalFoldersMisconfigured}
		<aside class="card preset-tonal-warning p-4 text-sm">
			<i class="fa-solid fa-triangle-exclamation mr-2"></i>{m.personalFoldersParentNotSet()}
		</aside>
	{/if}

	{#if view === 'edit'}
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
								{#if data.portal.is_public && !PUBLIC_SAFE.includes(item.kind)}
									<span class="mt-0.5 block text-warning-600" title={m.hiddenOnPublicHelp()}>
										<i class="fa-solid fa-eye-slash"></i>
										{m.hiddenOnPublic()}
									</span>
								{/if}
							</label>
							<label class="text-[10px] text-surface-500 grow">
								<span class="block">{tf.label}</span>
								{#if item.kind === 'create'}
									<select bind:value={item.target.model} class="select rounded-md text-sm">
										<option value="">—</option>
										{#each modelOptions as o}<option value={o.value}>{o.label}</option>{/each}
									</select>
								{:else if item.kind === 'navigate'}
									<select bind:value={item.target.url} class="select rounded-md text-sm">
										<option value="">—</option>
										{#each modelOptions as o}<option value="/{o.value}">{o.label}</option>{/each}
									</select>
								{:else if item.kind === 'document'}
									<select bind:value={item.target.token} class="select rounded-md text-sm">
										<option value="">—</option>
										{#each data.publicDocuments as d}<option value={d.token}>{d.name}</option
											>{/each}
									</select>
								{:else if item.kind === 'framework'}
									<select bind:value={item.target.snapshot} class="select rounded-md text-sm">
										<option value="">—</option>
										{#each data.snapshots as s}<option value={s.id}
												>{s.name} ({s.framework_name})</option
											>{/each}
									</select>
								{:else if item.kind === 'metric'}
									<select bind:value={item.target.source} class="select rounded-md text-sm">
										{#each METRIC_SOURCES as src}<option value={src.value}>{src.label}</option
											>{/each}
									</select>
									{#if !item.target.source}
										<input
											bind:value={item.target.value}
											placeholder="128"
											class="input mt-1 rounded-md text-sm"
										/>
									{/if}
								{:else}
									<input
										bind:value={item.target[tf.key]}
										placeholder={tf.ph}
										class="input rounded-md text-sm"
									/>
								{/if}
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
	{:else if view === 'preview'}
		<div class="rounded-2xl bg-linear-to-br from-surface-100-900 to-surface-200-800 p-8">
			<PortalGrid sections={previewSections} />
		</div>
	{:else}
		<form
			method="POST"
			action="?/updateSettings"
			use:settingsEnhance
			class="card bg-surface-50-950 p-6 space-y-5 max-w-4xl"
		>
			<label class="flex items-center gap-2 text-sm">
				<input type="checkbox" bind:checked={$settingsData.enabled} class="checkbox" />
				{m.enabled()}
			</label>
			<label class="flex items-center gap-2 text-sm">
				<input type="checkbox" bind:checked={$settingsData.is_default} class="checkbox" />
				{m.defaultPortal()}
			</label>
			<label class="block text-sm">
				<span class="block text-surface-600-400">{m.order()}</span>
				<input type="number" bind:value={$settingsData.order} class="input rounded-md w-24" />
			</label>
			<AutocompleteSelect
				form={settingsSuperform}
				multiple
				optionsEndpoint="user-groups"
				field="audience_groups"
				pathField="path"
				label={m.audience()}
			/>
			<p class="text-xs text-surface-500">{m.audienceHelp()}</p>

			<hr class="border-surface-200-800" />

			<div class="space-y-4">
				<div class="flex items-center gap-2">
					<i class="fa-solid fa-globe text-surface-400"></i>
					<h3 class="font-semibold text-surface-800-200">{m.trustCenter()}</h3>
				</div>
				<label class="flex items-center gap-2 text-sm">
					<input type="checkbox" bind:checked={$settingsData.is_public} class="checkbox" />
					{m.makePublic()}
				</label>
				<p class="text-xs text-surface-500">{m.makePublicHelp()}</p>

				{#if $settingsData.is_public}
					<label class="flex items-center gap-2 text-sm">
						<input type="checkbox" bind:checked={$settingsData.is_primary} class="checkbox" />
						{m.primaryPortal()}
					</label>
					<p class="text-xs text-surface-500">{m.primaryPortalHelp()}</p>

					<div class="grid gap-4 sm:grid-cols-2">
						<label class="block text-sm">
							<span class="block text-surface-600-400">{m.tagline()}</span>
							<input bind:value={$settingsData.branding.tagline} class="input rounded-md" />
						</label>
						<label class="block text-sm">
							<span class="block text-surface-600-400">{m.logoUrl()}</span>
							<input
								bind:value={$settingsData.branding.logo_url}
								placeholder="https://…"
								class="input rounded-md"
							/>
						</label>
						<label class="block text-sm">
							<span class="block text-surface-600-400">{m.accentColor()}</span>
							<input
								type="color"
								value={$settingsData.branding.accent_color || '#7c3aed'}
								oninput={(e) => ($settingsData.branding.accent_color = e.currentTarget.value)}
								class="input h-10 rounded-md p-1"
							/>
						</label>
					</div>
				{/if}
			</div>

			<button class="btn preset-filled-primary-500">{m.save()}</button>
		</form>

		{#if data.portal.is_public && data.portal.public_token}
			<div class="card bg-surface-50-950 p-6 space-y-3 max-w-4xl mt-4">
				<h3 class="font-semibold text-surface-800-200">{m.publicLink()}</h3>
				<p class="text-xs text-surface-500">{m.publicLinkHelp()}</p>
				<div class="flex items-center gap-2">
					<input
						readonly
						value={`${page.url.origin}/trust/${data.portal.public_token}`}
						class="input rounded-md text-sm grow font-mono"
					/>
					<a
						href={`/trust/${data.portal.public_token}`}
						target="_blank"
						rel="noopener"
						class="btn btn-sm preset-tonal"
						aria-label={m.open()}><i class="fa-solid fa-arrow-up-right-from-square"></i></a
					>
					<button
						type="button"
						onclick={() =>
							navigator.clipboard?.writeText(
								`${page.url.origin}/trust/${data.portal.public_token}`
							)}
						class="btn btn-sm preset-tonal"
						aria-label={m.copy()}><i class="fa-solid fa-copy"></i></button
					>
				</div>
				<form method="POST" action="?/regeneratePublicToken" use:enhance={regenEnhance}>
					<button class="btn btn-sm preset-tonal-error">
						<i class="fa-solid fa-rotate mr-1"></i>{m.regenerateLink()}
					</button>
				</form>

				{#if data.portal.is_primary}
					<div class="border-t border-surface-200-800 pt-3">
						<p class="text-xs text-surface-500">{m.vanityUrlHelp()}</p>
						<div class="mt-2 flex items-center gap-2">
							<input
								readonly
								value={`${page.url.origin}/trust`}
								class="input rounded-md text-sm grow font-mono"
							/>
							<a
								href="/trust"
								target="_blank"
								rel="noopener"
								class="btn btn-sm preset-tonal"
								aria-label={m.open()}><i class="fa-solid fa-arrow-up-right-from-square"></i></a
							>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>

{#if view !== 'settings'}
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
{/if}
