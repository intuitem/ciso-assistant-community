<script lang="ts">
	// Inline "add a secret" name/value form, shared by the data browser and the
	// workflow data panel. Owns its own draft state; hands the trimmed name and
	// raw value to the parent on submit.
	import { m } from '$paraglide/messages';

	interface Props {
		onAdd: (name: string, value: string) => void;
		formClass?: string;
		submitIcon?: string;
		confirmTestId?: string;
	}

	let { onAdd, formClass = '', submitIcon = 'fa-plus', confirmTestId }: Props = $props();

	let name = $state('');
	let value = $state('');

	function submit(event: Event) {
		event.preventDefault();
		const trimmed = name.trim();
		if (!trimmed || !value) return;
		onAdd(trimmed, value);
		name = '';
		value = '';
	}
</script>

<form class="flex items-center gap-1 {formClass}" autocomplete="off" onsubmit={submit}>
	<input
		type="text"
		class="input text-xs px-1.5 py-1 min-w-0 flex-1"
		placeholder={m.secretName()}
		autocomplete="off"
		bind:value={name}
	/>
	<input
		type="password"
		class="input text-xs px-1.5 py-1 min-w-0 flex-1"
		placeholder={m.secretValue()}
		autocomplete="new-password"
		data-1p-ignore
		data-lpignore="true"
		bind:value
	/>
	<button
		type="submit"
		aria-label={m.addSecret()}
		class="btn-icon preset-tonal w-6 h-6 text-xs shrink-0"
		disabled={!name.trim() || !value}
		data-testid={confirmTestId}
	>
		<i class="fa-solid {submitIcon}"></i>
	</button>
</form>
