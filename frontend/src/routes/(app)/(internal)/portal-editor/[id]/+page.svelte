<script lang="ts">
	import { enhance, deserialize } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getToastStore } from '$lib/components/Toast/stores';
	import PortalGrid from '$lib/components/PortalGrid/PortalGrid.svelte';
	import SectionEditor from '$lib/components/PortalEditor/SectionEditor.svelte';
	import PortalSettingsPanel from '$lib/components/PortalEditor/PortalSettingsPanel.svelte';
	import { SCAFFOLDABLE_MODELS } from '$lib/utils/modelTargets';
	import { urlParamModelVerboseName } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { savedToast, savedToastEnhance } from '$lib/utils/portalActions';
	import { superForm } from 'sveltekit-superforms';
	import { page } from '$app/state';
	import type { PageData } from './$types';

	const personalFoldersMisconfigured = $derived(
		!!page.data?.settings?.personal_folders && !page.data?.settings?.personal_folders_parent
	);

	const modelOptions = SCAFFOLDABLE_MODELS.map((model) => ({
		value: model,
		label: safeTranslate(urlParamModelVerboseName(model))
	})).sort((a, b) => a.label.localeCompare(b.label));

	// Static in-app pages a 'navigate' tile can point at (no model behind them). The value
	// is the route path minus the leading slash, so the viewer's goto(`/${target.model}`)
	// reaches it unchanged.
	const PAGE_DESTINATIONS = [
		{ value: 'my-assignments', label: m.myAssignments() },
		{ value: 'auditee-dashboard', label: m.auditDashboard() }
	];

	let { data }: { data: PageData } = $props();
	const toast = getToastStore();
	let view = $state<'edit' | 'preview' | 'settings'>('edit');
	let name = $state(data.portal.name);

	// Title auto-saves on blur — no dedicated Save button, available in any view.
	async function saveName() {
		const trimmed = name.trim();
		if (!trimmed) {
			name = data.portal.name;
			return;
		}
		if (trimmed === data.portal.name) return;
		const fd = new FormData();
		fd.append('name', trimmed);
		const res = await fetch('?/updateMeta', { method: 'POST', body: fd });
		const result: any = deserialize(await res.text());
		if (result.type === 'success') {
			data.portal.name = trimmed;
			savedToast(toast);
		}
	}

	// Public documents available to certification tiles — reactive so inline uploads appear at once.
	let docs = $state<any[]>(data.publicDocuments ?? []);

	async function uploadDoc(item: { target: Record<string, string>; title: string }, e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		const fd = new FormData();
		fd.append('file', file);
		fd.append('name', item.title?.trim() || file.name);
		const res = await fetch('?/uploadDocument', { method: 'POST', body: fd });
		const result: any = deserialize(await res.text());
		if (result.type === 'success' && result.data?.uploaded) {
			const doc = result.data.uploaded;
			docs.push({ id: doc.id, name: doc.name, token: doc.token });
			item.target.token = doc.token;
			savedToast(toast);
		} else {
			toast.trigger({
				message: result.data?.error ?? m.error(),
				background: 'preset-filled-error-500'
			});
		}
		input.value = '';
	}

	const settingsSuperform = superForm(data.settingsForm, {
		dataType: 'json',
		resetForm: false,
		invalidateAll: true,
		onUpdated: ({ form }) => {
			if (form.valid) savedToast(toast);
		}
	});

	type Item = {
		id?: string;
		icon: string;
		title: string;
		description: string;
		kind:
			| 'create'
			| 'navigate'
			| 'external'
			| 'metric'
			| 'certificationDocument'
			| 'framework'
			| 'assessment';
		target: Record<string, any>;
	};
	type Section = { title: string; description: string; items: Item[] };

	let sections = $state<Section[]>(
		((data.portal.content?.sections ?? []) as any[]).map((s) => ({
			title: s.title ?? '',
			description: s.description ?? '',
			items: (s.items ?? []).map((i: any) => ({
				id: i.id,
				icon: i.icon ?? '',
				title: i.title ?? '',
				description: i.description ?? '',
				kind: i.kind ?? 'navigate',
				target: i.target ?? {}
			}))
		}))
	);

	// Kinds offered depend on the portal type: internal launcher vs public trust center.
	// 'external' belongs to both.
	const KINDS = $derived(
		data.portal.is_public
			? ['metric', 'certificationDocument', 'framework', 'external']
			: ['create', 'navigate', 'assessment', 'external']
	);

	const METRIC_SOURCES = [
		{ value: '', label: m.manual() },
		{ value: 'frameworks_count', label: m.frameworksMonitored() },
		{ value: 'controls_count', label: m.controlsCovered() }
	];

	const KIND_LABELS: Record<string, string> = {
		create: m.create(),
		navigate: m.navigate(),
		external: m.external(),
		metric: m.metric(),
		certificationDocument: m.certificationDocument(),
		framework: m.framework(),
		assessment: m.questionnaire()
	};

	// Bundle the shared option lists / data once for the section + tile editors.
	const ctx = $derived({
		modelOptions,
		pageDestinations: PAGE_DESTINATIONS,
		metricSources: METRIC_SOURCES,
		kinds: KINDS,
		kindLabels: KIND_LABELS,
		snapshots: data.snapshots,
		frameworks: data.frameworks,
		folders: data.folders,
		docs
	});

	const payload = $derived(JSON.stringify({ sections }));

	// 'navigate' targets a model (mandatory) — backfill any tile that lacks one so the
	// select is never silently empty. 'assessment' tiles need a stable id so a click can
	// resolve the author's stored config server-side.
	$effect(() => {
		const fallback = modelOptions[0]?.value;
		for (const sec of sections)
			for (const it of sec.items) {
				if (it.kind === 'navigate' && !it.target.model && fallback) it.target.model = fallback;
				if (it.kind === 'assessment' && !it.id) it.id = crypto.randomUUID();
			}
	});

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
			kind: KINDS[0] as Item['kind'],
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
</script>

<div class="space-y-6 pb-28">
	<div class="flex items-center gap-3">
		<a href="/portal-editor" class="text-surface-500 hover:text-primary-500">
			<i class="fa-solid fa-arrow-left"></i>
		</a>
		<div class="grow">
			<input
				bind:value={name}
				onblur={saveName}
				aria-label={m.name()}
				class="input rounded-md text-lg font-bold max-w-md"
			/>
		</div>
		{#if data.portal.status === 'published'}
			<a href="/portal/{data.portal.id}" class="text-xs text-primary-500" aria-label="Open portal"
				><i class="fa-solid fa-arrow-up-right-from-square"></i></a
			>
		{/if}
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
			<SectionEditor
				{section}
				{sections}
				{si}
				{ctx}
				onMoveSection={(dir) => moveSection(si, dir)}
				onRemoveSection={() => removeSection(si)}
				onAddItem={() => addItem(si)}
				onMoveItem={(ii, dir) => moveItem(si, ii, dir)}
				onRemoveItem={(ii) => removeItem(si, ii)}
				onMoveToGroup={(ii, targetSi) => moveItemToGroup(si, ii, targetSi)}
				onUpload={uploadDoc}
			/>
		{/each}

		<button onclick={addSection} class="btn preset-tonal">
			<i class="fa-solid fa-plus mr-1"></i>{m.addGroup()}
		</button>
	{:else if view === 'preview'}
		<div class="rounded-2xl bg-linear-to-br from-surface-100-900 to-surface-200-800 p-8">
			<PortalGrid sections={previewSections} />
		</div>
	{:else}
		<PortalSettingsPanel
			superform={settingsSuperform}
			portal={data.portal}
			origin={page.url.origin}
			{toast}
		/>
	{/if}
</div>

{#if view !== 'settings'}
	<div
		class="fixed bottom-0 right-0 left-64 flex items-center justify-end gap-3 border-t border-surface-200-800 bg-surface-50-950/90 px-8 py-3 backdrop-blur"
	>
		<form method="POST" action="?/setStatus" use:enhance={savedToastEnhance(toast)}>
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
			use:enhance={savedToastEnhance(toast, { reset: false })}
		>
			<input type="hidden" name="payload" value={payload} />
			<button class="btn preset-filled-primary-500">
				<i class="fa-solid fa-floppy-disk mr-1"></i>{m.save()}
			</button>
		</form>
	</div>
{/if}
