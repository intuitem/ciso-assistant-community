<script lang="ts">
	import * as m from '$paraglide/messages';
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants';
	import {
		getModalStore,
		type ModalStore,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface WordTemplateInfo {
		template_key: string;
		description: string;
		default_languages: string[];
		overrides: string[];
	}

	interface WordTemplateOverride {
		id: string;
		template_key: string;
		language: string;
		file: string | null;
		is_active: boolean;
	}

	const supportedLanguages = Object.keys(LOCALE_DISPLAY_MAP);

	let availableTemplates: WordTemplateInfo[] = $state([]);
	let overrides: WordTemplateOverride[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let successMessage = $state('');

	// Edit state
	let editingKey = $state('');
	let editingLang = $state('en');
	let uploading = $state(false);

	async function fetchData() {
		loading = true;
		error = '';
		try {
			const [availableRes, overridesRes] = await Promise.all([
				fetch('/fe-api/custom-word-templates/available'),
				fetch('/fe-api/custom-word-templates')
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

	function getOverride(key: string, lang: string): WordTemplateOverride | undefined {
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
			// Ensure override record exists
			let existing = getOverride(editingKey, editingLang);
			if (!existing) {
				const createRes = await fetch('/fe-api/custom-word-templates', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						template_key: editingKey,
						language: editingLang,
						is_active: true
					})
				});
				if (!createRes.ok) {
					const errData = await createRes.json();
					error = JSON.stringify(errData);
					uploading = false;
					return;
				}
				const created = await createRes.json();
				existing = created;
			}

			// Upload the file
			const uploadRes = await fetch(`/fe-api/custom-word-templates/${existing!.id}`, {
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
				try {
					const res = await fetch(`/fe-api/custom-word-templates/${existing.id}`, {
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
	<span class="text-gray-500">{m.wordTemplatesDescription()}</span>

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
		<!-- Upload panel -->
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
					{#if getOverride(editingKey, editingLang)?.file}
						<span class="badge preset-filled-warning-500 text-xs">{m.customized()}</span>
					{/if}
				</div>
			</header>

			<div class="p-4 space-y-4">
				<!-- Language selector row -->
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<label class="label font-medium" for="word-template-lang">{m.language()}</label>
						<select id="word-template-lang" class="select w-48" bind:value={editingLang}>
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

				<!-- Current file info -->
				{#if getOverride(editingKey, editingLang)?.file}
					<div class="flex items-center gap-2 text-sm text-gray-600">
						<i class="fa-solid fa-file-word text-primary-500"></i>
						<span>{getOverride(editingKey, editingLang)?.file}</span>
					</div>
				{/if}

				<!-- Upload -->
				<div>
					<label class="label font-medium" for="word-file-upload">{m.uploadTemplate()}</label>
					<input
						id="word-file-upload"
						type="file"
						accept=".docx"
						class="input mt-1"
						onchange={handleFileInput}
						disabled={uploading}
					/>
					<p class="text-xs text-gray-500 mt-1">{m.wordTemplateUploadHelp()}</p>
				</div>

				{#if uploading}
					<div class="flex items-center gap-2 text-sm">
						<i class="fa-solid fa-spinner fa-spin"></i>
						<span>{m.uploading()}</span>
					</div>
				{/if}
			</div>

			<footer class="flex items-center gap-2 p-4 border-t border-surface-200">
				<a
					href="/fe-api/custom-word-templates/download-default/{editingKey}/{editingLang}"
					class="btn preset-outlined-surface-500"
					download
				>
					<i class="fa-solid fa-download text-xs mr-1"></i>
					{m.downloadDefaultTemplate()}
				</a>
				<div class="flex-1"></div>
				<button class="btn preset-outlined-surface-500" type="button" onclick={cancelEdit}>
					{m.cancel()}
				</button>
			</footer>
		</div>
	{:else}
		<!-- Templates list -->
		<div class="card bg-white shadow-lg overflow-hidden">
			{#each availableTemplates as template, i}
				{@const customLangs = getCustomizedLanguages(template.template_key)}
				{#if i > 0}
					<hr class="border-surface-200" />
				{/if}
				<div class="flex items-center gap-4 px-4 py-3 hover:bg-surface-50 transition-colors">
					<i class="fa-solid fa-file-word text-primary-500"></i>
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
	{/if}
</div>
