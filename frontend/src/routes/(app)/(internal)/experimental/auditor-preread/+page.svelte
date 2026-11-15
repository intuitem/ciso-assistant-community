<script lang="ts">
	import { safeTranslate } from '#lib/utils/i18n.js';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<div class="p-6 flex flex-col gap-4">
	<div class="max-w-3xl">
		<h1 class="text-xl font-semibold">Auditor pre-read</h1>
		<p class="text-surface-600-400">
			For each requirement of an audit: what a certification auditor will ask, which records they
			will request, how they will sample and who they will interview, set against what the audit
			already holds. Available for ISO/IEC 27001:2022 audits.
		</p>
	</div>

	{#if !data.frameworks.length}
		<p class="card preset-tonal-warning p-4">
			ISO/IEC 27001:2022 is not loaded. Load it from the libraries, then create an audit on it.
		</p>
	{:else if !data.audits.length}
		<p class="card preset-tonal-surface p-4">No ISO/IEC 27001:2022 audit you can view yet.</p>
	{:else}
		<table class="table">
			<thead>
				<tr><th>Audit</th><th>Domain</th><th>Perimeter</th><th>Status</th><th></th></tr>
			</thead>
			<tbody>
				{#each data.audits as audit (audit.id)}
					<tr>
						<td class="font-medium">{audit.name}</td>
						<td>{audit.folder?.str ?? ''}</td>
						<td>{audit.perimeter?.str ?? ''}</td>
						<td>{audit.status ? safeTranslate(audit.status) : ''}</td>
						<td class="text-right">
							<a
								class="btn btn-sm preset-filled-primary-500"
								href="/experimental/auditor-preread/{audit.id}">Open pre-read</a
							>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>
