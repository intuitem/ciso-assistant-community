<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		refs?: { references?: any[]; referenced_by?: any[] };
	}
	let { refs }: Props = $props();

	let outgoing = $derived(refs?.references ?? []);
	let incoming = $derived(refs?.referenced_by ?? []);
</script>

{#if outgoing.length || incoming.length}
	<div class="space-y-3 rounded border border-surface-200-800 p-3 text-sm">
		{#if outgoing.length}
			<div>
				<p class="mb-1 font-semibold text-surface-600-400">
					<i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>{m.references()} ({outgoing.length})
				</p>
				<ul class="list-disc space-y-1 pl-5">
					{#each outgoing as r (r.id)}
						<li>
							<a href={`/documents/${r.id}/read`} class="text-primary-500 hover:underline"
								>{r.str}</a
							>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
		{#if incoming.length}
			<div>
				<p class="mb-1 font-semibold text-surface-600-400">
					<i class="fa-solid fa-arrow-down-left mr-1"></i>{m.referencedBy()} ({incoming.length})
				</p>
				<ul class="list-disc space-y-1 pl-5">
					{#each incoming as r (r.id)}
						<li>
							<a href={`/documents/${r.id}/read`} class="text-primary-500 hover:underline"
								>{r.str}</a
							>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</div>
{/if}
