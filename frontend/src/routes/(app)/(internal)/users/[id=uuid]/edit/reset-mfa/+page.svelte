<script lang="ts">
	import type { PageData } from './$types';
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	let userInput = $state('');

	const yes = $derived(m.yes().toLowerCase());
	const canConfirm = $derived(!!userInput && userInput.trim().toLowerCase() === yes);
</script>

<div class="flex w-full h-full items-center justify-center">
	<div class="flex flex-col bg-white p-12 w-2/5 rounded-lg shadow-lg items-center space-y-4">
		<div class="bg-error-300 px-6 py-5 rounded-full text-3xl">
			<i class="fa-solid fa-shield-halved"></i>
		</div>
		<h2 class="text-xl font-bold">{m.resetMFA()}</h2>
		<p class="text-red-600 text-sm font-semibold text-center">
			{m.resetMFAWarning()}
		</p>

		<form method="POST" use:enhance class="flex flex-col w-full space-y-3">
			<label class="label">
				<span class="text-sm font-medium text-red-600">{m.confirmYes()}</span>
				<input
					type="text"
					data-testid="reset-mfa-confirm-textfield"
					bind:value={userInput}
					placeholder={m.confirmYesPlaceHolder()}
					class="input w-full"
					aria-label={m.confirmYes()}
				/>
			</label>

			<div class="flex flex-row justify-between space-x-4 pt-3">
				<a
					href="/users/{data.object.id}"
					class="btn bg-gray-400 text-white font-semibold w-full text-center"
				>
					{m.cancel()}
				</a>
				<button
					type="submit"
					data-testid="reset-mfa-submit-button"
					class="btn bg-red-600 hover:bg-red-700 text-white font-semibold w-full disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={!canConfirm}
				>
					{m.resetMFA()}
				</button>
			</div>
		</form>
	</div>
</div>
