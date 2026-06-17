<script lang="ts">
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import CustomFieldsSection from './CustomFieldsSection.svelte';

	interface Choice {
		value: string;
		label_localized: string;
	}
	interface Definition {
		id: string;
		key: string;
		label_localized: string;
		field_type: string;
		choices: Choice[];
	}

	interface Props {
		/** endpoint to PATCH (the project detail url) */
		endpoint: string;
		model: string;
		folderId?: string;
		values?: Record<string, any>;
		onSaved?: () => void;
	}

	let { endpoint, model, folderId = undefined, values = {}, onSaved = () => {} }: Props = $props();

	const enabled = $derived(page.data?.featureflags?.custom_fields === true);

	let definitions: Definition[] = $state([]);
	let editing = $state(false);
	let saving = $state(false);
	let error = $state('');

	const schema = z.object({ custom_fields: z.record(z.string(), z.any()).default({}) });
	const form = superForm(defaults({ custom_fields: { ...values } }, zod(schema)), {
		dataType: 'json',
		SPA: true,
		validators: zod(schema)
	});
	const { form: formData } = form;

	async function load() {
		const params = new URLSearchParams({ model, visible: 'true' });
		if (folderId) params.set('for_folder', folderId);
		try {
			const res = await fetch(`/custom-fields/?${params.toString()}`);
			if (!res.ok) return;
			const data = await res.json();
			definitions = data.results ?? data;
		} catch (e) {
			console.error('Failed to load custom field definitions', e);
		}
	}

	$effect(() => {
		void folderId;
		if (enabled) load();
	});

	function startEdit() {
		form.form.set({ custom_fields: { ...values } });
		error = '';
		editing = true;
	}

	async function save() {
		saving = true;
		error = '';
		try {
			const res = await fetch(endpoint, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ custom_fields: $formData.custom_fields })
			});
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				error = body?.custom_fields
					? JSON.stringify(body.custom_fields)
					: `${m.error()} (HTTP ${res.status})`;
				return;
			}
			editing = false;
			onSaved();
		} catch (e) {
			error = m.error();
		} finally {
			saving = false;
		}
	}

	function displayValue(def: Definition, raw: any): string {
		if (raw === undefined || raw === null || raw === '') return '--';
		if (def.field_type === 'boolean') return raw ? '✅' : '❌';
		if (def.field_type === 'choice') {
			return def.choices.find((c) => c.value === raw)?.label_localized ?? String(raw);
		}
		if (def.field_type === 'multi_choice') {
			const list = Array.isArray(raw) ? raw : [raw];
			if (!list.length) return '--';
			return list
				.map((v) => def.choices.find((c) => c.value === v)?.label_localized ?? v)
				.join(', ');
		}
		return String(raw);
	}
</script>

{#if definitions.length}
	<div class="border-t border-gray-200 pt-4 mt-4">
		<div class="flex justify-between items-center mb-3">
			<h3 class="text-md font-semibold text-gray-800">{m.customFields()}</h3>
			{#if !editing}
				<button class="btn preset-tonal-primary btn-sm" onclick={startEdit}>
					<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
				</button>
			{:else}
				<div class="flex gap-2">
					<button
						class="btn preset-tonal-surface btn-sm"
						onclick={() => (editing = false)}
						disabled={saving}>{m.cancel()}</button
					>
					<button class="btn preset-filled-primary-500 btn-sm" onclick={save} disabled={saving}>
						{#if saving}<i class="fa-solid fa-spinner fa-spin mr-2"></i>{/if}{m.save()}
					</button>
				</div>
			{/if}
		</div>

		{#if error}
			<div class="card preset-tonal-error p-3 mb-3 text-sm">{error}</div>
		{/if}

		{#if editing}
			<CustomFieldsSection {form} {model} {folderId} />
		{:else}
			<dl class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
				{#each definitions as def (def.id)}
					<div class="border-l-2 border-gray-200 pl-4">
						<dt class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
							{def.label_localized}
						</dt>
						<dd class="text-sm text-gray-900">{displayValue(def, values?.[def.key])}</dd>
					</div>
				{/each}
			</dl>
		{/if}
	</div>
{/if}
