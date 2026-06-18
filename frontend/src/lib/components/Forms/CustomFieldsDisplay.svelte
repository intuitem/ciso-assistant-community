<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';

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
		model: string;
		folderId?: string;
		values?: Record<string, any>;
	}

	let { model, folderId = undefined, values = {} }: Props = $props();

	const enabled = $derived(page.data?.featureflags?.custom_fields === true);
	let definitions: Definition[] = $state([]);

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
	<div class="card p-4 shadow-lg bg-white">
		<h3 class="text-lg font-semibold mb-3">{m.customFields()}</h3>
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
	</div>
{/if}
