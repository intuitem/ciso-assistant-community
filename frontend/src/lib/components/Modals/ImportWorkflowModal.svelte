<script lang="ts">
	import { WorkflowImportSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { getModalStore } from './stores';

	const modalStore = getModalStore();

	interface Props {
		form: any;
		parent: any;
	}

	let { form, parent }: Props = $props();

	// Secrets referenced by the selected file ({{secrets.NAME}} — the same
	// derivation the backend uses for the requires manifest). Values typed here
	// are created in the target domain during import; blanks are skipped and
	// surface as publish errors instead.
	let requiredSecrets = $state<string[]>([]);
	let secretValues = $state<Record<string, string>>({});

	async function handleFilePicked(event: Event) {
		const target = event.target as HTMLElement | null;
		if (!(target instanceof HTMLInputElement) || target.type !== 'file') return;
		const file = target.files?.[0];
		if (!file) {
			requiredSecrets = [];
			secretValues = {};
			return;
		}
		const text = await file.text();
		requiredSecrets = [
			...new Set([...text.matchAll(/\{\{\s*secrets\.(\w+)/g)].map((match) => match[1]))
		].sort();
		secretValues = Object.fromEntries(requiredSecrets.map((name) => [name, '']));
	}

	const secretsJson = $derived(
		JSON.stringify(
			Object.fromEntries(Object.entries(secretValues).filter(([, value]) => value !== ''))
		)
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="card bg-surface-50-950 p-6 w-full max-w-lg shadow-xl space-y-4 rounded-xl"
	onchange={handleFilePicked}
>
	<div class="flex items-center justify-between">
		<header class="flex items-center gap-3">
			<div
				class="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-100 text-primary-600"
			>
				<i class="fa-solid fa-file-import text-lg"></i>
			</div>
			<h3 class="text-xl font-bold text-surface-950-50">
				{m.importWorkflow()}
			</h3>
		</header>
		<button
			type="button"
			class="flex items-center justify-center w-8 h-8 rounded-md text-surface-400-600 hover:text-surface-600-400 hover:bg-surface-100-900 transition-colors"
			onclick={parent.onClose}
			aria-label={m.close()}
		>
			<i class="fa-solid fa-xmark"></i>
		</button>
	</div>
	<p class="text-sm text-surface-600-400">{m.importWorkflowHelpText()}</p>
	<hr class="border-surface-200-800" />
	<SuperForm
		class="flex flex-col space-y-4"
		dataType="form"
		enctype="multipart/form-data"
		data={form}
		validators={zod(WorkflowImportSchema)}
		action="?/importWorkflow"
		useFocusTrap={false}
		onSubmit={() => {
			modalStore.close();
		}}
	>
		{#snippet children({ form })}
			<FileInput
				{form}
				field="file"
				label={m.workflowYamlFile()}
				allowedExtensions={['yaml', 'yml']}
			/>
			<AutocompleteSelect
				{form}
				optionsEndpoint="folders"
				optionsDetailedUrlParameters={[
					['content_type', 'DO'],
					['content_type', 'GL']
				]}
				field="folder"
				label={m.domain()}
			/>
			{#if requiredSecrets.length}
				<div class="space-y-2" data-testid="import-required-secrets">
					<p class="text-sm font-medium text-surface-900-100">
						<i class="fa-solid fa-lock mr-1 text-surface-500"></i>{m.requiredSecrets()}
					</p>
					<p class="text-xs text-surface-600-400">{m.requiredSecretsHint()}</p>
					{#each requiredSecrets as name (name)}
						<div class="flex items-center gap-2">
							<span class="font-mono text-xs text-surface-800-200 w-40 truncate" title={name}>
								{name}
							</span>
							<input
								type="password"
								class="input text-xs flex-1"
								placeholder={m.secretValue()}
								bind:value={secretValues[name]}
								data-testid="import-secret-{name}"
							/>
						</div>
					{/each}
				</div>
			{/if}
			<input type="hidden" name="secrets" value={secretsJson} />
			<button
				class="btn preset-filled-primary-500 font-semibold w-full rounded-lg py-2.5"
				data-testid="import-workflow-submit"
				type="submit"
			>
				<i class="fa-solid fa-upload mr-2"></i>
				{m.importWorkflow()}
			</button>
		{/snippet}
	</SuperForm>
</div>
