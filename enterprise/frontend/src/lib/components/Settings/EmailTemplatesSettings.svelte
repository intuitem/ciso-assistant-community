<script lang="ts">
	import * as m from '$paraglide/messages';
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants';
	import {
		getModalStore,
		type ModalStore,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	const modalStore: ModalStore = getModalStore();

	interface TemplateInfo {
		template_key: string;
		description: string;
		category: string;
		variables: string[];
		overrides: string[];
	}

	interface TemplateCategory {
		key: string;
		label: () => string;
		description: () => string;
		templates: TemplateInfo[];
	}

	interface TemplateOverride {
		id: string;
		template_key: string;
		language: string;
		subject: string;
		body: string;
		is_active: boolean;
	}

	const supportedLanguages = Object.keys(LOCALE_DISPLAY_MAP);

	let availableTemplates: TemplateInfo[] = $state([]);
	let overrides: TemplateOverride[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	const CATEGORY_META: Record<string, { label: () => string; description: () => string }> = {
		core: { label: () => m.coreEmails(), description: () => m.coreEmailsDescription() },
		notification: {
			label: () => m.notificationEmails(),
			description: () => m.notificationEmailsDescription()
		}
	};

	let groupedTemplates: TemplateCategory[] = $derived.by(() => {
		const groups: Record<string, TemplateInfo[]> = {};
		for (const t of availableTemplates) {
			const cat = t.category || 'notification';
			(groups[cat] ??= []).push(t);
		}
		return ['core', 'notification']
			.filter((key) => groups[key]?.length)
			.map((key) => ({
				key,
				label: CATEGORY_META[key]?.label ?? (() => key),
				description: CATEGORY_META[key]?.description ?? (() => ''),
				templates: groups[key]
			}));
	});

	// Edit state
	let editingKey = $state('');
	let editingLang = $state('en');
	let editSubject = $state('');
	let editBody = $state('');
	let editVariables: string[] = $state([]);
	let saving = $state(false);
	let successMessage = $state('');
	let showPreview = $state(false);

	async function fetchData() {
		loading = true;
		error = '';
		try {
			const [availableRes, overridesRes] = await Promise.all([
				fetch('/fe-api/custom-email-templates/available'),
				fetch('/fe-api/custom-email-templates')
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
		return overrides.filter((o) => o.template_key === key && o.is_active).map((o) => o.language);
	}

	async function startEdit(key: string, lang?: string) {
		editingKey = key;
		editingLang = lang ?? 'en';
		editVariables = availableTemplates.find((t) => t.template_key === key)?.variables || [];

		const existing = getOverride(key, editingLang);
		if (existing) {
			editSubject = existing.subject;
			editBody = existing.body;
		} else {
			await loadDefault();
		}
	}

	async function switchLanguage() {
		const existing = getOverride(editingKey, editingLang);
		if (existing) {
			editSubject = existing.subject;
			editBody = existing.body;
		} else {
			await loadDefault();
		}
	}

	async function loadDefault() {
		editSubject = '';
		editBody = '';
		try {
			const res = await fetch(
				`/fe-api/custom-email-templates/default/${editingKey}/${editingLang}`
			);
			if (!res.ok) {
				throw new Error('Failed to load default template');
			}
			const data = await res.json();
			editSubject = data.subject;
			editBody = data.body;
		} catch {
			error = 'Failed to load default template';
		}
	}

	function cancelEdit() {
		editingKey = '';
		editSubject = '';
		editBody = '';
		editVariables = [];
	}

	async function saveTemplate() {
		saving = true;
		successMessage = '';
		try {
			const existing = getOverride(editingKey, editingLang);
			const payload = {
				template_key: editingKey,
				language: editingLang,
				subject: editSubject,
				body: editBody,
				is_active: true
			};

			let res;
			if (existing) {
				res = await fetch(`/fe-api/custom-email-templates/${existing.id}`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(payload)
				});
			} else {
				res = await fetch('/fe-api/custom-email-templates', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(payload)
				});
			}

			if (res.ok) {
				successMessage = m.templateSaved();
				await fetchData();
				cancelEdit();
			} else {
				const errData = await res.json();
				error = JSON.stringify(errData);
			}
		} catch {
			error = 'Failed to save template';
		}
		saving = false;
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
				try {
					const res = await fetch(`/fe-api/custom-email-templates/${existing.id}`, {
						method: 'DELETE'
					});
					if (res.ok || res.status === 204) {
						successMessage = m.templateReset();
						await fetchData();
						cancelEdit();
					}
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

	$effect(() => {
		fetchData();
	});
</script>

<div class="flex flex-col gap-6">
	<span class="text-gray-500">{m.emailTemplatesDescription()}</span>

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
		<!-- Edit panel -->
		<div class="card bg-white shadow-lg">
			<header class="flex items-center justify-between p-4 border-b border-surface-200">
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
						<h3 class="h4 font-semibold">{templateName(editingKey)}</h3>
						<p class="text-sm text-gray-500">{templateDescription(editingKey)}</p>
					</div>
				</div>
				<div class="flex items-center gap-2">
					{#if getOverride(editingKey, editingLang)}
						<span class="badge preset-filled-warning-500 text-xs">{m.customized()}</span>
					{/if}
				</div>
			</header>

			<div class="p-4 space-y-4">
				<!-- Language selector row -->
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<label class="label font-medium" for="template-lang">{m.language()}</label>
						<select
							id="template-lang"
							class="select w-48"
							bind:value={editingLang}
							onchange={switchLanguage}
						>
							{#each supportedLanguages as lang}
								<option value={lang}>{langLabel(lang)}</option>
							{/each}
						</select>
					</div>
					{#if getOverride(editingKey, editingLang)}
						<button
							class="btn btn-sm preset-outlined-error-500"
							type="button"
							onclick={() => resetTemplate(editingKey, editingLang)}
							title={m.resetToDefault()}
						>
							<i class="fa-solid fa-rotate-left text-xs"></i>
							{m.resetToDefault()}
						</button>
					{/if}
				</div>

				<hr />

				<!-- Subject -->
				<div>
					<label class="label font-medium" for="template-subject">{m.templateSubject()}</label>
					<input id="template-subject" type="text" class="input mt-1" bind:value={editSubject} />
				</div>

				<!-- Body with preview toggle -->
				<div>
					<div class="flex items-center justify-between">
						<label class="label font-medium" for="template-body">{m.templateBody()}</label>
						<button
							class="btn btn-sm preset-outlined-surface-500"
							type="button"
							onclick={() => (showPreview = !showPreview)}
						>
							<i class="fa-solid {showPreview ? 'fa-pen' : 'fa-eye'} text-xs"></i>
							{showPreview ? m.editTemplate() : m.templatePreview()}
						</button>
					</div>
					{#if showPreview}
						<div class="card p-4 mt-1 bg-surface-50-950">
							<MarkdownRenderer content={editBody} />
						</div>
					{:else}
						<textarea
							id="template-body"
							class="textarea mt-1 font-mono text-sm"
							rows="14"
							bind:value={editBody}
						></textarea>
						<p class="text-xs text-gray-500 mt-1">
							<i class="fa-brands fa-markdown"></i>
							{m.markdownSupported()}
						</p>
					{/if}
				</div>

				<!-- Variables reference -->
				<details class="p-3 rounded-lg bg-surface-50-950">
					<summary class="cursor-pointer font-medium text-sm">
						<i class="fa-solid fa-code text-xs mr-1"></i>
						{m.templateVariables()}
					</summary>
					<div class="mt-2 flex flex-wrap gap-2">
						{#each editVariables as variable}
							<code class="bg-surface-200 px-2 py-1 rounded text-xs font-mono"
								>${'{' + variable + '}'}</code
							>
						{/each}
					</div>
				</details>
			</div>

			<footer class="flex items-center gap-2 p-4 border-t border-surface-200">
				<button
					class="btn preset-filled-primary-500 font-semibold"
					type="button"
					disabled={saving}
					onclick={saveTemplate}
				>
					{#if saving}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{/if}
					<i class="fa-solid fa-check mr-1"></i>
					{m.save()}
				</button>
				<button class="btn preset-outlined-surface-500" type="button" onclick={loadDefault}>
					<i class="fa-solid fa-file-lines mr-1 text-xs"></i>
					{m.loadDefault()}
				</button>
				<div class="flex-1"></div>
				<button class="btn preset-outlined-surface-500" type="button" onclick={cancelEdit}>
					{m.cancel()}
				</button>
			</footer>
		</div>
	{:else}
		<!-- Templates list grouped by category -->
		{#each groupedTemplates as category}
			<div class="flex flex-col gap-3">
				<div>
					<h3 class="text-base font-semibold flex items-center gap-2">
						<i
							class="fa-solid {category.key === 'core'
								? 'fa-shield-halved'
								: 'fa-bell'} text-sm text-primary-500"
						></i>
						{category.label()}
					</h3>
					<p class="text-sm text-gray-500">{category.description()}</p>
				</div>
				<div class="card bg-white shadow-lg overflow-hidden">
					{#each category.templates as template, i}
						{@const customLangs = getCustomizedLanguages(template.template_key)}
						{#if i > 0}
							<hr class="border-surface-200" />
						{/if}
						<div class="flex items-center gap-4 px-4 py-3 hover:bg-surface-50 transition-colors">
							<div class="flex-1 min-w-0">
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
								<p class="text-sm text-gray-500 truncate">
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
			</div>
		{/each}
	{/if}
</div>
