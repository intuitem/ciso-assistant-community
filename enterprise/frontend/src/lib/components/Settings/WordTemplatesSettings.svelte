<script lang="ts">
	import * as m from '$paraglide/messages';
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants';

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

	async function resetTemplate(key: string, lang: string) {
		const existing = getOverride(key, lang);
		if (!existing) return;

		try {
			const res = await fetch(`/fe-api/custom-word-templates/${existing.id}`, {
				method: 'DELETE'
			});
			if (res.ok || res.status === 204) {
				successMessage = m.templateReset();
				await fetchData();
			}
		} catch {
			error = 'Failed to reset template';
		}
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
	<p class="text-gray-500">{m.wordTemplatesDescription()}</p>

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
				<label class="label font-medium" for="word-template-lang">{m.language()}</label>
				<select id="word-template-lang" class="select w-48" bind:value={editingLang}>
					{#each supportedLanguages as lang}
						<option value={lang}>{langLabel(lang)}</option>
					{/each}
				</select>
				{#if getOverride(editingKey, editingLang)?.file}
					<span class="badge preset-filled-warning-500 text-xs">{m.customized()}</span>
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

			<!-- Current file info -->
			{#if getOverride(editingKey, editingLang)?.file}
				<div class="flex items-center gap-2 text-sm text-gray-600">
					<i class="fa-solid fa-file-word"></i>
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
				<div class="flex items-center gap-2">
					<i class="fa-solid fa-spinner fa-spin"></i>
					<span>{m.uploading()}</span>
				</div>
			{/if}

			<!-- Download default -->
			<div class="flex gap-2">
				<a
					href="/fe-api/custom-word-templates/download-default/{editingKey}/{editingLang}"
					class="btn preset-outlined-surface-500"
					download
				>
					<i class="fa-solid fa-download text-xs"></i>
					{m.downloadDefaultTemplate()}
				</a>
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
