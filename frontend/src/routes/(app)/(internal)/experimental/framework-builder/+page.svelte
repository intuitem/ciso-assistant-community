<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	$pageTitle = 'Framework Builder';

	let { data } = $props();
	let frameworks: any[] = $state(data.frameworks ?? []);
	let drafts: any[] = $state(data.drafts ?? []);

	// Status messages with auto-dismiss
	let statusMessage = $state('');
	let statusType: 'success' | 'error' | '' = $state('');
	let creating = $state(false);
	let statusTimeout: ReturnType<typeof setTimeout> | null = null;

	function setStatus(message: string, type: 'success' | 'error') {
		statusMessage = message;
		statusType = type;
		if (statusTimeout) clearTimeout(statusTimeout);
		if (type === 'success') {
			statusTimeout = setTimeout(() => {
				statusMessage = '';
				statusType = '';
			}, 3000);
		}
	}

	async function createFramework() {
		creating = true;
		try {
			const res = await fetch('/experimental/framework-builder', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || JSON.stringify(err));
			}
			const result = await res.json();
			window.location.href = `/frameworks/${result.id}/builder/`;
		} catch (e: any) {
			setStatus(e.message, 'error');
			creating = false;
		}
	}
</script>

<div class="space-y-6">
	<!-- Top bar -->
	<div class="card p-4">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div class="flex items-center gap-2">
				<button
					type="button"
					class="btn btn-sm bg-primary-500 text-white hover:bg-primary-600 transition-colors"
					onclick={createFramework}
					disabled={creating}
				>
					{#if creating}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{:else}
						<i class="fa-solid fa-plus mr-1"></i>
					{/if}
					New Framework
				</button>
			</div>
			{#if statusMessage}
				<span
					class="text-xs px-2 py-1 rounded-full transition-opacity {statusType === 'error'
						? 'bg-red-100 text-red-700'
						: 'bg-green-100 text-green-700'}"
				>
					<i class="fa-solid {statusType === 'error' ? 'fa-circle-xmark' : 'fa-circle-check'} mr-1"
					></i>
					{statusMessage}
				</span>
			{/if}
		</div>
	</div>

	<!-- Frameworks with active drafts -->
	{#if drafts.length > 0}
		<div class="card p-4">
			<h3 class="text-lg font-semibold mb-3">
				<i class="fa-solid fa-pen-to-square mr-1"></i>
				Frameworks with Active Drafts
			</h3>
			<div class="table-container">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>{m.name()}</th>
							<th>{m.description()}</th>
							<th>{m.status()}</th>
							<th class="w-48"></th>
						</tr>
					</thead>
					<tbody>
						{#each drafts as framework}
							<tr class="bg-primary-50">
								<td class="font-medium">{framework.name}</td>
								<td class="text-sm text-gray-500 max-w-48 truncate">
									{framework.description || '—'}
								</td>
								<td>
									<span class="badge variant-filled-primary text-xs">
										<i class="fa-solid fa-pen-to-square mr-0.5"></i>
										Editing
									</span>
									{#if framework.library}
										<span class="badge variant-ghost-surface text-xs ml-1">
											<i class="fa-solid fa-book-open mr-0.5"></i>From Library
										</span>
									{:else}
										<span class="badge variant-ghost-surface text-xs ml-1">Custom</span>
									{/if}
								</td>
								<td>
									<a
										href="/frameworks/{framework.id}/builder/"
										class="btn btn-sm variant-filled-primary"
									>
										<i class="fa-solid fa-pen-to-square mr-1"></i>
										Continue Editing
									</a>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}

	<!-- All frameworks -->
	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-book mr-1"></i>
			All Frameworks
		</h3>
		{#if frameworks.length > 0}
			<div class="table-container">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>{m.name()}</th>
							<th>{m.description()}</th>
							<th>Provider</th>
							<th>{m.status()}</th>
							<th class="w-32"></th>
						</tr>
					</thead>
					<tbody>
						{#each frameworks as framework}
							<tr>
								<td class="font-medium">{framework.name}</td>
								<td class="text-sm text-gray-500 max-w-48 truncate">
									{framework.description || '—'}
								</td>
								<td class="text-sm">{framework.provider || '—'}</td>
								<td>
									{#if framework.library}
										<span class="badge variant-ghost-surface text-xs">
											<i class="fa-solid fa-book-open mr-0.5"></i>From Library
										</span>
									{:else}
										<span class="badge variant-ghost-surface text-xs">Custom</span>
									{/if}
									{#if framework.has_editing_draft}
										<span class="badge variant-filled-primary text-xs ml-1">
											<i class="fa-solid fa-pen-to-square mr-0.5"></i>
											Editing
										</span>
									{/if}
									{#if framework.editing_version > 1}
										<span class="text-xs text-gray-400 ml-1">
											v{framework.editing_version}
										</span>
									{/if}
								</td>
								<td>
									<a
										href="/frameworks/{framework.id}/builder/"
										class="btn btn-sm variant-ghost-primary"
									>
										<i class="fa-solid fa-pen-to-square mr-1"></i>
										Edit
									</a>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p class="text-sm text-gray-400 py-4 text-center">
				No frameworks yet.
				<a href="/loaded-libraries" class="text-primary-500 hover:underline"
					>Load some from the library.</a
				>
			</p>
		{/if}
	</div>
</div>
