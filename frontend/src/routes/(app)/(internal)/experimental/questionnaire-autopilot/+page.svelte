<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { pageTitle } from '$lib/utils/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
		form: any;
	}

	let { data, form }: Props = $props();

	$pageTitle = 'Questionnaire Autopilot';

	const toast = getToastStore();

	let selectedFolderId = $state('');
	let title = $state('');
	let submitting = $state(false);

	$effect(() => {
		if (form?.error) {
			toast.trigger({ message: form.error });
		}
	});

	const statusBadge = (status: string) => {
		switch (status) {
			case 'pending':
			case 'parsing':
				return 'bg-yellow-100 text-yellow-800';
			case 'parsed':
				return 'bg-green-100 text-green-800';
			case 'failed':
				return 'bg-red-100 text-red-800';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	};
</script>

<div class="grid grid-cols-3 gap-4">
	<div class="col-span-2 bg-white shadow-sm py-4 px-6 space-y-4 card">
		<div>
			<h4 class="h4 font-bold">
				<i class="fa-solid fa-file-import mr-2"></i>Questionnaire Autopilot
			</h4>
			<p class="text-sm text-gray-600 mt-1">
				Upload a customer security questionnaire (.xlsx) and scope it to a folder. Once parsed,
				you'll review the detected sheet/columns before any prefill happens.
			</p>
			<p class="text-xs text-gray-500 mt-1">
				Experimental — no LLM prefill yet, just upload + parse + column mapping.
			</p>
		</div>

		<form
			method="post"
			action="?/upload"
			enctype="multipart/form-data"
			use:enhance={() => {
				submitting = true;
				return async ({ update }) => {
					await update();
					submitting = false;
				};
			}}
			class="space-y-4"
		>
			<div class="rounded-lg p-4 border-2 border-green-500">
				<label for="folder" class="block text-sm font-medium text-gray-900">
					Target folder *
				</label>
				<select
					id="folder"
					name="folder"
					bind:value={selectedFolderId}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
					required
				>
					<option value="">Select a folder</option>
					{#each data.folders as folder}
						<option value={folder.id}>{folder.str || folder.name}</option>
					{/each}
				</select>
				<p class="text-xs text-gray-500 mt-1">
					The agent will (later) look up applied controls, evidences, and existing assessments
					inside this folder when answering questions.
				</p>
			</div>

			<div class="rounded-lg p-4 border-2 border-blue-500">
				<label for="title" class="block text-sm font-medium text-gray-900">
					Title (optional)
				</label>
				<input
					id="title"
					name="title"
					type="text"
					bind:value={title}
					maxlength="200"
					placeholder="e.g. Acme Corp — Vendor Security Review Q2"
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
				/>
			</div>

			<div class="rounded-lg p-4 border-2 border-pink-500">
				<label for="file" class="block text-sm font-medium text-gray-900">
					Questionnaire file (.xlsx) *
				</label>
				<input
					id="file"
					name="file"
					type="file"
					accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
					class="mt-1.5 w-full text-sm"
					required
				/>
			</div>

			<div class="flex gap-2">
				<button type="submit" class="btn preset-filled" disabled={submitting}>
					<i class="fa-solid fa-upload mr-2"></i>
					{submitting ? 'Uploading…' : 'Upload & parse'}
				</button>
				<button
					type="button"
					class="btn"
					onclick={() => goto('/experimental')}
					disabled={submitting}
				>
					Cancel
				</button>
			</div>
		</form>
	</div>

	<div class="col-span-1 p-4">
		<h5 class="font-semibold mb-2 text-sm">Recent runs</h5>
		{#if data.runs.length === 0}
			<p class="text-sm text-gray-500">No runs yet. Upload a questionnaire to start.</p>
		{:else}
			<div class="space-y-2">
				{#each data.runs as run}
					<a
						href="/experimental/questionnaire-autopilot/{run.id}"
						class="block p-3 bg-white rounded shadow-sm hover:shadow-md transition-shadow"
					>
						<div class="flex justify-between items-start gap-2">
							<div class="text-sm font-medium truncate">
								{run.title || run.filename}
							</div>
							<span class="text-xs px-2 py-0.5 rounded {statusBadge(run.status)}">
								{run.status}
							</span>
						</div>
						<div class="text-xs text-gray-500 mt-1 truncate">
							{run.folder?.str || run.folder?.name || '—'}
						</div>
						<div class="text-xs text-gray-400">
							{new Date(run.created_at).toLocaleString()}
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</div>
</div>
