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
		variables: string[];
		overrides: string[];
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

			if (availableRes.ok) {
				availableTemplates = await availableRes.json();
			}
			if (overridesRes.ok) {
				const data = await overridesRes.json();
				overrides = data.results || data;
			}
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
		try {
			const res = await fetch(
				`/fe-api/custom-email-templates/default/${editingKey}/${editingLang}`
			);
			if (res.ok) {
				const data = await res.json();
				editSubject = data.subject;
				editBody = data.body;
			}
		} catch {
			// keep current values
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

	function formatKey(key: string): string {
		return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}

	function langLabel(code: string): string {
		return (LOCALE_DISPLAY_MAP as Record<string, string>)[code] ?? code.toUpperCase();
	}

	$effect(() => {
		fetchData();
	});
</script>

<div class="space-y-4">
	<p class="text-gray-500">{m.emailTemplatesDescription()}</p>

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
		<div class="card p-6 space-y-4">
			<div class="flex items-center justify-between">
				<h3 class="h4 font-semibold">
					{m.editTemplate()}: {formatKey(editingKey)}
				</h3>
				<button class="btn preset-outlined-surface-500" type="button" onclick={cancelEdit}>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</div>

			<!-- Language selector -->
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
				{#if getOverride(editingKey, editingLang)}
					<span class="badge preset-filled-warning-500 text-xs">{m.customized()}</span>
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

			<!-- Variables reference -->
			<details class="card p-3 bg-surface-100">
				<summary class="cursor-pointer font-medium">{m.templateVariables()}</summary>
				<div class="mt-2 flex flex-wrap gap-2">
					{#each editVariables as variable}
						<code class="bg-surface-200 px-2 py-1 rounded text-sm">${'{' + variable + '}'}</code>
					{/each}
				</div>
			</details>

			<div>
				<label class="label font-medium" for="template-subject">{m.templateSubject()}</label>
				<input id="template-subject" type="text" class="input mt-1" bind:value={editSubject} />
			</div>

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
					<div class="card p-4 mt-1">
						<MarkdownRenderer content={editBody} />
					</div>
				{:else}
					<textarea
						id="template-body"
						class="textarea mt-1 font-mono text-sm"
						rows="12"
						bind:value={editBody}
					></textarea>
					<p class="text-xs text-gray-500 mt-1">{m.markdownSupported()}</p>
				{/if}
			</div>

			<div class="flex gap-2">
				<button
					class="btn preset-filled-primary-500 font-semibold"
					type="button"
					disabled={saving}
					onclick={saveTemplate}
				>
					{#if saving}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{/if}
					{m.save()}
				</button>
				<button class="btn preset-outlined-surface-500" type="button" onclick={loadDefault}>
					{m.loadDefault()}
				</button>
				<button class="btn preset-outlined-surface-500" type="button" onclick={cancelEdit}>
					{m.cancel()}
				</button>
			</div>
		</div>
	{:else}
		<!-- Templates list -->
		<div class="table-container">
			<table class="table">
				<thead>
					<tr>
						<th>{m.templateKey()}</th>
						<th>{m.description()}</th>
						<th>{m.status()}</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each availableTemplates as template}
						{@const customLangs = getCustomizedLanguages(template.template_key)}
						<tr>
							<td class="font-medium">{formatKey(template.template_key)}</td>
							<td class="text-gray-600 text-sm">{template.description}</td>
							<td>
								{#if customLangs.length > 0}
									<div class="flex flex-wrap gap-1">
										{#each customLangs as lang}
											<span class="badge preset-filled-warning-500 text-xs">
												{lang.toUpperCase()}
											</span>
										{/each}
									</div>
								{:else}
									<span class="badge preset-outlined-surface-500 text-xs"
										>{m.defaultTemplate()}</span
									>
								{/if}
							</td>
							<td>
								<button
									class="btn btn-sm preset-outlined-primary-500"
									type="button"
									onclick={() => startEdit(template.template_key)}
									title={m.editTemplate()}
								>
									<i class="fa-solid fa-pen text-xs"></i>
									{m.editTemplate()}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
