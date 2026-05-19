<script lang="ts">
	interface Props {
		ref_id?: string | null;
		name?: string | null;
		bold?: boolean;
		class?: string;
	}

	let { ref_id, name, bold = false, class: className = '' }: Props = $props();
</script>

{#if ref_id || name}
	<span class="inline-flex items-center gap-1 {className}">
		{#if ref_id}
			<span
				class="inline-block px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 leading-none {bold
					? 'font-semibold'
					: ''}">{ref_id}</span
			>
		{/if}
		{#if name}
			<span class={bold ? 'font-semibold' : ''}>{name}</span>
		{/if}
	</span>
{/if}
