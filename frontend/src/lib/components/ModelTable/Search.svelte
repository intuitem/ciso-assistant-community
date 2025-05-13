<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { m } from '$paraglide/messages';
	interface Props {
		handler: DataHandler;
	}

	let { handler }: Props = $props();

	let value = $state('');
	let timeout: any;

	const search = () => {
		handler.search(value);
		clearTimeout(timeout);
		timeout = setTimeout(() => {
			handler.invalidate();
		}, 400);
	};
</script>

<input
	class="input bg-surface-50 max-w-2xl"
	placeholder={m.searchPlaceholder()}
	data-testid="search-input"
	id="search-input"
	bind:value
	oninput={search}
/>
