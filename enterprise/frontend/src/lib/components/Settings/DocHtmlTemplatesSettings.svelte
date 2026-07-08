<script lang="ts">
	import * as m from '$paraglide/messages';
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants';
	import {
		getModalStore,
		type ModalStore,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface TemplateVariable {
		name: string;
		type: string;
		description: string;
	}

	interface TemplateInfo {
		template_key: string;
		description: string;
		default_languages: string[];
		variables: TemplateVariable[];
		overrides: string[];
	}

	interface TemplateOverride {
		id: string;
		template_key: string;
		language: string;
		file: string | null;
		is_active: boolean;
	}

	const supportedLanguages = Object.keys(LOCALE_DISPLAY_MAP);

	let availableTemplates: TemplateInfo[] = $state([]);
	let overrides: TemplateOverride[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let successMessage = $state('');

	let editingKey = $state('');
	let editingLang = $state('en');
	let uploading = $state(false);

	async function fetchData() {
		loading = true;
		error = '';
		try {
			const [availableRes, overridesRes] = await Promise.all([
				fetch('/fe-api/custom-doc-html-templates/available'),
				fetch('/fe-api/custom-doc-html-templates')
			]);

			if (!availableRes.ok || !overridesRes.ok) {
				throw new Error('Failed to load templates');
			}
			availableTemplates = await availableRes.json();
			const data = await overridesRes.json();
			overrides = data.results || data;
		} catch {
			error = 'Failed to load templates';
		}
		loading = false;
	}

	function getOverride(key: string, lang: string): TemplateOverride | undefined {
		return overrides.find((o) => o.template_key === key && o.language === lang);
	}

	function getCustomizedLanguages(key: string): string[] {
		return overrides
			.filter((o) => o.template_key === key && o.is_active && o.file)
			.map((o) => o.language);
	}

	function startEdit(key: string) {
		editingKey = key;
		editingLang = 'en';
	}

	function cancelEdit() {
		editingKey = '';
	}

	async function uploadFile(file: File) {
		uploading = true;
		successMessage = '';
		error = '';
		try {
			let existing = getOverride(editingKey, editingLang);
			if (!existing) {
				const createRes = await fetch('/fe-api/custom-doc-html-templates', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						template_key: editingKey,
						language: editingLang,
						is_active: true
					})
				});
				if (!createRes.ok) {
					const errData = await createRes.json().catch(() => ({}));
					error = errData.detail || errData.error || Object.values(errData).flat()[0] || m.error();
					uploading = false;
					return;
				}
				existing = await createRes.json();
			}

			const uploadRes = await fetch(`/fe-api/custom-doc-html-templates/${existing!.id}`, {
				method: 'POST',
				headers: {
					'Content-Disposition': `attachment; filename=${encodeURIComponent(file.name)}`
				},
				body: file
			});

			if (uploadRes.ok) {
				successMessage = m.templateSaved();
				await fetchData();
				cancelEdit();
			} else {
				const errData = await uploadRes.json();
				error = errData.file || JSON.stringify(errData);
			}
		} catch {
			error = 'Failed to upload template';
		}
		uploading = false;
	}

	function handleFileInput(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files?.[0]) {
			uploadFile(input.files[0]);
		}
	}

	function resetTemplate(key: string, lang: string) {
		const existing = getOverride(key, lang);
		if (!existing) return;

		const modal: ModalSettings = {
			type: 'confirm',
			title: m.resetToDefault(),
			body: m.confirmResetTemplate(),
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				error = '';
				successMessage = '';
				try {
					const res = await fetch(`/fe-api/custom-doc-html-templates/${existing.id}`, {
						method: 'DELETE'
					});
					if (!res.ok && res.status !== 204) {
						throw new Error('Failed to reset template');
					}
					successMessage = m.templateReset();
					await fetchData();
					cancelEdit();
				} catch {
					error = 'Failed to reset template';
				}
			}
		};
		modalStore.trigger(modal);
	}

	function snakeToCamel(key: string): string {
		const parts = key.split('_');
		return (
			parts[0] +
			parts
				.slice(1)
				.map((p) => p.charAt(0).toUpperCase() + p.slice(1))
				.join('')
		);
	}

	function templateName(key: string): string {
		const msgKey = `template${snakeToCamel(key).charAt(0).toUpperCase() + snakeToCamel(key).slice(1)}Name`;
		const fn = (m as Record<string, (() => string) | undefined>)[msgKey];
		return fn ? fn() : key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}

	function templateDescription(key: string): string {
		const msgKey = `template${snakeToCamel(key).charAt(0).toUpperCase() + snakeToCamel(key).slice(1)}Description`;
		const fn = (m as Record<string, (() => string) | undefined>)[msgKey];
		return fn ? fn() : '';
	}

	function langLabel(code: string): string {
		return (LOCALE_DISPLAY_MAP as Record<string, string>)[code] ?? code.toUpperCase();
	}

	function getTemplateVariables(key: string): TemplateVariable[] {
		return availableTemplates.find((t) => t.template_key === key)?.variables || [];
	}

	const TYPE_BADGE_CLASSES: Record<string, string> = {
		string: 'preset-filled-primary-500',
		number: 'preset-filled-success-500',
		object: 'preset-filled-warning-500',
		list: 'preset-filled-tertiary-500',
		image: 'preset-filled-surface-500'
	};

	$effect(() => {
		fetchData();
	});
</script>

<div class="flex flex-col gap-6">
	<span class="text-surface-600-400">{m.docHtmlTemplatesDescription()}</span>

	{#if successMessage}
		<div class="alert preset-filled-success-500 p-3">
			{successMessage}
		</div>
	{/if}

	{#if error}
		<div class="alert preset-filled-error-500 p-3">
			{error}
		</div>
	{/if}

	{#if loading}
		<div class="flex justify-center p-8">
			<i class="fa-solid fa-spinner fa-spin text-2xl"></i>
		</div>
	{:else if editingKey}
		<div class="card bg-surface-50-950 shadow-lg">
			<header class="flex items-center justify-between border-b border-surface-200-800 p-4">
				<div class="flex items-center gap-3">
					<button
						class="btn btn-sm preset-outlined-surface-500"
						type="button"
						onclick={cancelEdit}
						title={m.cancel()}
					>
						<i class="fa-solid fa-arrow-left text-xs"></i>
					</button>
					<div>
						<h3 class="text-base font-semibold">{templateName(editingKey)}</h3>
						<p class="text-xs text-surface-600-400">{langLabel(editingLang)}</p>
					</div>
				</div>
				<div class="flex items-center gap-2">
					{#if getOverride(editingKey, editingLang)?.file}
						<span class="badge preset-filled-warning-500 text-xs">{m.customized()}</span>
					{/if}
				</div>
			</header>

			<div class="space-y-4 p-4">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<label class="label font-medium" for="doc-html-template-lang">{m.language()}</label>
						<select id="doc-html-template-lang" class="select w-48" bind:value={editingLang}>
							{#each supportedLanguages as lang}
								<option value={lang}>{langLabel(lang)}</option>
							{/each}
						</select>
					</div>
					{#if getOverride(editingKey, editingLang)?.file}
						<button
							class="btn btn-sm preset-outlined-error-500"
							type="button"
							onclick={() => resetTemplate(editingKey, editingLang)}
						>
							<i class="fa-solid fa-rotate-left text-xs"></i>
							{m.resetToDefault()}
						</button>
					{/if}
				</div>

				<hr />

				{#if getOverride(editingKey, editingLang)?.file}
					<div class="flex items-center gap-2 text-sm text-surface-600-400">
						<i class="fa-solid fa-file-code text-primary-500"></i>
						<span>{getOverride(editingKey, editingLang)?.file}</span>
					</div>
				{/if}

				<div>
					<label class="label font-medium" for="doc-html-file-upload">{m.uploadTemplate()}</label>
					<input
						id="doc-html-file-upload"
						type="file"
						accept=".html"
						class="input mt-1"
						onchange={handleFileInput}
						disabled={uploading}
					/>
					<p class="mt-1 text-xs text-surface-600-400">{m.docHtmlTemplateUploadHelp()}</p>
				</div>

				{#if uploading}
					<div class="flex items-center gap-2 text-sm">
						<i class="fa-solid fa-spinner fa-spin"></i>
						<span>{m.uploading()}</span>
					</div>
				{/if}

				{#if getTemplateVariables(editingKey).length > 0}
					<details class="rounded-lg bg-surface-50-950 p-3">
						<summary class="cursor-pointer text-sm font-medium">
							<i class="fa-solid fa-code mr-1 text-xs"></i>
							{m.templateVariables()}
						</summary>
						<p class="mb-3 mt-2 text-xs text-surface-600-400">
							{m.docHtmlTemplateSyntaxHelp()}
						</p>
						<div class="mb-3 space-y-1 font-mono text-xs text-surface-600-400">
							<p>{'{{ variable }}'} &mdash; simple value</p>
							<p>{'{{ content|safe }}'} &mdash; pre-rendered HTML body</p>
							<p>{'{% if logo_base64 %} ... {% endif %}'} &mdash; conditional block</p>
						</div>
						<div class="mt-2 space-y-2">
							{#each getTemplateVariables(editingKey) as variable}
								<div class="flex items-start gap-2 text-sm">
									<code class="shrink-0 rounded bg-surface-200-800 px-2 py-0.5 font-mono text-xs"
										>{variable.name}</code
									>
									<span
										class="badge shrink-0 text-xs {TYPE_BADGE_CLASSES[variable.type] ??
											'preset-filled-surface-500'}">{variable.type}</span
									>
									<span class="text-xs text-surface-600-400">{variable.description}</span>
								</div>
							{/each}
						</div>
					</details>
				{/if}
			</div>

			<footer class="flex items-center gap-2 border-t border-surface-200-800 p-4">
				<a
					href="/fe-api/custom-doc-html-templates/download-default/{editingKey}/{editingLang}"
					class="btn preset-outlined-surface-500"
					download
				>
					<i class="fa-solid fa-download mr-1 text-xs"></i>
					{m.downloadDefaultTemplate()}
				</a>
				<div class="flex-1"></div>
				<button class="btn preset-outlined-surface-500" type="button" onclick={cancelEdit}>
					{m.cancel()}
				</button>
			</footer>
		</div>
	{:else}
		<div class="card overflow-hidden bg-surface-50-950 shadow-lg">
			{#each availableTemplates as template, i}
				{@const customLangs = getCustomizedLanguages(template.template_key)}
				{#if i > 0}
					<hr class="border-surface-200-800" />
				{/if}
				<div class="flex items-center gap-4 px-4 py-3 transition-colors hover:bg-surface-100-900">
					<i class="fa-solid fa-file-code text-primary-500"></i>
					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<span class="font-medium">{templateName(template.template_key)}</span>
							{#if customLangs.length > 0}
								{#each customLangs as lang}
									<span class="badge preset-filled-warning-500 text-xs">
										{lang.toUpperCase()}
									</span>
								{/each}
							{/if}
						</div>
						<p class="truncate text-sm text-surface-600-400">
							{templateDescription(template.template_key)}
						</p>
					</div>
					<button
						class="btn btn-sm preset-outlined-primary-500 shrink-0"
						type="button"
						onclick={() => startEdit(template.template_key)}
						title={m.editTemplate()}
					>
						<i class="fa-solid fa-pen text-xs"></i>
						{m.editTemplate()}
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
