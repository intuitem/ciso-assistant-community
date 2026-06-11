<script lang="ts">
	import { m } from '$paraglide/messages';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { BACKEND_API_EXPOSED_URL } from '$lib/utils/constants';

	interface Props {
		data: any;
	}

	let { data }: Props = $props();

	let scimTokens = $derived(data.scimTokens ?? []);
	let newToken: string | null = $state(null);
	let copied = $state(false);

	const scimEndpoint = `${BACKEND_API_EXPOSED_URL}/scim/v2/`;

	async function copyToClipboard(text: string) {
		await navigator.clipboard.writeText(text);
	}

	async function copyToken() {
		if (newToken) {
			await copyToClipboard(newToken);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		}
	}
</script>

<div class="flex flex-col gap-6">
	<span class="text-gray-500">{m.scimDescription()}</span>

	<!-- Endpoint URL -->
	<div class="card bg-white shadow p-4 flex flex-col gap-2">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-link text-sm text-primary-500"></i>
			{m.scimEndpointUrl()}
		</h3>
		<div class="flex items-center gap-2">
			<code class="bg-gray-100 rounded px-3 py-1 text-sm flex-1 break-all">{scimEndpoint}</code>
			<button class="btn btn-sm preset-outlined-surface-500" onclick={() => copyToClipboard(scimEndpoint)}>
				<i class="fa-solid fa-copy mr-1"></i>
				{m.copy()}
			</button>
		</div>
	</div>

	<!-- New token banner -->
	{#if newToken}
		<div class="card bg-amber-50 border border-amber-300 p-4 flex flex-col gap-3">
			<p class="font-semibold text-amber-800">
				<i class="fa-solid fa-triangle-exclamation mr-1"></i>
				{m.scimTokenGenerated()}
			</p>
			<p class="text-sm text-amber-700">{m.scimTokenWarning()}</p>
			<div class="flex items-center gap-2">
				<code class="bg-white rounded px-3 py-1 text-sm flex-1 break-all border border-amber-300"
					>{newToken}</code
				>
				<button class="btn btn-sm preset-filled-warning-500" onclick={copyToken}>
					<i class="fa-solid fa-copy mr-1"></i>
					{copied ? m.copied() : m.copy()}
				</button>
			</div>
			<button class="btn btn-sm preset-outlined-surface-500 self-start" onclick={() => (newToken = null)}>
				{m.close()}
			</button>
		</div>
	{/if}

	<!-- Tokens table -->
	<div class="flex items-center justify-between">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-key text-sm text-primary-500"></i>
			{m.scimTokens()}
		</h3>
		<form
			method="POST"
			action="?/generateScimToken"
			use:enhance={() => {
				return async ({ result, update }) => {
					if (result.type === 'success' && result.data?.token) {
						newToken = result.data.token as string;
					}
					await update({ reset: false });
					await invalidateAll();
				};
			}}
		>
			<button type="submit" class="btn btn-sm preset-filled-primary-500">
				<i class="fa-solid fa-plus mr-1"></i>
				{m.generateScimToken()}
			</button>
		</form>
	</div>

	{#if scimTokens.length === 0}
		<p class="text-sm text-gray-400">{m.noScimTokens()}</p>
	{:else}
		<div class="card bg-white shadow overflow-hidden">
			<table class="table w-full text-sm">
				<thead>
					<tr class="bg-gray-50">
						<th class="px-4 py-2 text-left font-medium text-gray-600">{m.scimTokenName()}</th>
						<th class="px-4 py-2 text-left font-medium text-gray-600">{m.createdAt()}</th>
						<th class="px-4 py-2 text-left font-medium text-gray-600">Digest</th>
						<th class="px-4 py-2"></th>
					</tr>
				</thead>
				<tbody>
					{#each scimTokens as token (token.id)}
						<tr class="border-t border-gray-100">
							<td class="px-4 py-2">{token.name}</td>
							<td class="px-4 py-2 text-xs text-gray-500">{new Date(token.created).toLocaleString()}</td>
							<td class="px-4 py-2 font-mono text-xs text-gray-500">{token.digest.slice(-8)}</td>
							<td class="px-4 py-2 text-right">
								<form
									method="POST"
									action="?/revokeScimToken"
									use:enhance={() => {
										return async ({ update }) => {
											await update({ reset: false });
											await invalidateAll();
										};
									}}
								>
									<input type="hidden" name="id" value={token.id} />
									<button type="submit" class="btn btn-sm preset-outlined-error-500">
										{m.revokeScimToken()}
									</button>
								</form>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
