<script lang="ts">
	import { superForm, defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';
	import { goto } from '$app/navigation';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import { DOCUMENT_TYPES } from '$lib/utils/documentTypes';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';

	interface Props {
		// Function/context — optional; the standalone flow leaves these unset. A
		// future evidence/policy surface passes them to bind the created document.
		functionType?: string;
		parent?: { id: string } | undefined;
		parentField?: 'policies' | 'applied_controls' | 'task_templates' | 'processings';
		defaultFolder?: string;
		sources?: Array<'author' | 'upload' | 'link'>;
		endpoint?: string;
		onCreated?: (r: { id: string; source: string }) => void;
	}

	let {
		functionType = undefined,
		parent = undefined,
		parentField = undefined,
		defaultFolder = '',
		sources = ['author', 'upload', 'link'],
		endpoint = '/documents/new',
		onCreated = undefined
	}: Props = $props();

	const boundIds = (field: string) => (parent && parentField === field ? [parent.id] : []);

	const schema = z.object({
		ref_id: z.string().optional().default(''),
		name: z.string().optional().default(''),
		document_type: z.string().default(functionType ?? 'policy'),
		folder: z.string().default(defaultFolder),
		locale: z.string().default('en'),
		url: z.string().optional().default(''),
		classification: z.string().optional().default(''),
		policies: z.array(z.string()).optional().default(boundIds('policies')),
		applied_controls: z.array(z.string()).optional().default(boundIds('applied_controls')),
		task_templates: z.array(z.string()).optional().default(boundIds('task_templates')),
		processings: z.array(z.string()).optional().default(boundIds('processings')),
		filtering_labels: z.array(z.string()).optional().default([])
	});
	const _form = superForm(defaults(zod(schema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(schema)
	});
	const { form } = _form;

	const documentTypeOptions = DOCUMENT_TYPES.map((t) => ({ label: t.label(), value: t.key }));
	const localeOptions = Object.keys(LOCALE_MAP).map((c) => ({ label: c.toUpperCase(), value: c }));
	const sourceMeta: Record<string, { label: () => string; icon: string }> = {
		author: { label: () => m.author(), icon: 'fa-pen' },
		upload: { label: () => m.upload(), icon: 'fa-upload' },
		link: { label: () => m.link(), icon: 'fa-link' }
	};

	let source = $state(sources[0]);
	let file = $state<File | null>(null);
	let busy = $state(false);
	let error = $state('');

	function pickFile(e: Event) {
		file = (e.target as HTMLInputElement).files?.[0] ?? null;
	}

	async function submit() {
		error = '';
		if (!$form.folder) return void (error = m.domainRequired());
		if (source === 'upload' && !file) return void (error = m.fileRequired());
		if (source === 'link' && !$form.url.trim()) return void (error = m.urlRequired());

		busy = true;
		try {
			const fd = new FormData();
			fd.append('source', source);
			fd.append('ref_id', $form.ref_id);
			fd.append('name', $form.name);
			fd.append('document_type', $form.document_type);
			fd.append('folder', $form.folder);
			fd.append('locale', $form.locale);
			if ($form.classification) fd.append('classification', $form.classification);
			if (source === 'link') fd.append('url', $form.url.trim());
			if (source === 'upload' && file) fd.append('file', file);
			for (const f of [
				'policies',
				'applied_controls',
				'task_templates',
				'processings',
				'filtering_labels'
			] as const) {
				for (const id of $form[f] ?? []) fd.append(f, id);
			}

			const res = await fetch(endpoint, { method: 'POST', body: fd });
			if (!res.ok) {
				const d = await res.json().catch(() => null);
				error = d?.error || d?.url || d?.folder || m.error();
				return;
			}
			const container = await res.json();
			if (onCreated) onCreated({ id: container.id, source });
			else goto(`/document-containers/${container.id}/document`);
		} catch {
			error = m.error();
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-5">
	{#if error}
		<aside class="variant-soft-error rounded p-3 text-sm">{error}</aside>
	{/if}

	<TextField form={_form} field="ref_id" label={m.refId()} />

	<TextField form={_form} field="name" label={m.name()} />

	{#if !functionType}
		<Select
			form={_form}
			options={documentTypeOptions}
			field="document_type"
			label={m.documentType()}
		/>
	{/if}

	<FolderTreeSelect form={_form} field="folder" label={m.domain()} />

	<AutocompleteSelect
		form={_form}
		field="classification"
		optionsEndpoint="classification-levels"
		optionsLabelField="label"
		label={m.classification()}
		nullable
	/>

	<!-- Content source: the same document, provided three ways -->
	<div>
		<span class="mb-2 block text-sm font-semibold">{m.contentSource()}</span>
		<div class="grid gap-2 sm:grid-cols-3">
			{#each sources as s (s)}
				<button
					type="button"
					aria-pressed={source === s}
					class="flex flex-col items-center gap-1.5 rounded-lg border-2 px-3 py-4 transition-all {source ===
					s
						? 'border-primary-500 bg-primary-500/10 text-primary-700 dark:text-primary-300'
						: 'border-surface-200-800 bg-surface-100-900 text-surface-600-400 hover:border-primary-500/40 hover:bg-surface-200-800'}"
					onclick={() => (source = s)}
				>
					<i class="fa-solid {sourceMeta[s].icon} text-lg"></i>
					<span class="text-sm font-medium">{sourceMeta[s].label()}</span>
				</button>
			{/each}
		</div>
	</div>

	{#if source === 'author'}
		<p class="text-sm text-surface-500">
			<i class="fa-solid fa-circle-info mr-1"></i>{m.authorHint()}
		</p>
	{:else}
		<Select form={_form} options={localeOptions} field="locale" label={m.language()} />
		{#if source === 'upload'}
			<label class="label">
				<span>{m.file()}</span>
				<input type="file" class="input" onchange={pickFile} />
			</label>
		{:else}
			<TextField form={_form} field="url" type="url" label={m.url()} placeholder="https://…" />
		{/if}
	{/if}

	<Dropdown open={false} icon="fa-solid fa-link" header={m.relationships()}>
		<AutocompleteSelect
			form={_form}
			multiple
			createFromSelection={true}
			optionsEndpoint="filtering-labels"
			optionsLabelField="label"
			field="filtering_labels"
			label={m.labels()}
			translateOptions={false}
			allowUserOptions="append"
		/>
		<AutocompleteSelect
			form={_form}
			multiple
			optionsEndpoint="policies"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="policies"
			label={m.policies()}
		/>
		<AutocompleteSelect
			form={_form}
			multiple
			optionsEndpoint="applied-controls"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="applied_controls"
			label={m.appliedControls()}
		/>
		<AutocompleteSelect
			form={_form}
			multiple
			optionsEndpoint="task-templates"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="task_templates"
			label={m.taskTemplates()}
		/>
		<AutocompleteSelect
			form={_form}
			multiple
			optionsEndpoint="processings"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="processings"
			label={m.processings()}
		/>
	</Dropdown>

	<div class="border-t border-surface-200-800 pt-5">
		<button
			type="button"
			class="btn variant-filled-primary w-full font-semibold shadow-sm transition-shadow hover:shadow-md"
			disabled={busy}
			onclick={submit}
		>
			{#if busy}
				<i class="fa-solid fa-spinner fa-spin mr-2"></i>
			{:else}
				<i class="fa-solid fa-check mr-2"></i>
			{/if}
			{m.create()}
		</button>
	</div>
</div>
