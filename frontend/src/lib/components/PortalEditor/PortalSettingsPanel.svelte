<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { savedToastEnhance } from '$lib/utils/portalActions';

	let {
		superform,
		portal,
		origin,
		toast
	}: { superform: any; portal: any; origin: string; toast: any } = $props();

	const { form: settingsData, enhance: settingsEnhance } = superform;
	const regenEnhance = savedToastEnhance(toast);
	const publicUrl = $derived(`${origin}/trust/${portal.public_token}`);
</script>

<form
	method="POST"
	action="?/updateSettings"
	use:settingsEnhance
	class="card bg-surface-50-950 p-6 space-y-5 max-w-4xl"
>
	<label class="flex items-center gap-2 text-sm">
		<input type="checkbox" bind:checked={$settingsData.enabled} class="checkbox" />
		{m.enabled()}
	</label>
	<label class="flex items-center gap-2 text-sm">
		<input type="checkbox" bind:checked={$settingsData.is_default} class="checkbox" />
		{m.defaultPortal()}
	</label>
	<label class="block text-sm">
		<span class="block text-surface-600-400">{m.order()}</span>
		<input type="number" bind:value={$settingsData.order} class="input rounded-md w-24" />
	</label>
	<AutocompleteSelect
		form={superform}
		multiple
		optionsEndpoint="user-groups"
		field="audience_groups"
		pathField="path"
		label={m.audience()}
	/>
	<p class="text-xs text-surface-500">{m.audienceHelp()}</p>

	<hr class="border-surface-200-800" />

	<div class="space-y-4">
		<div class="flex items-center gap-2">
			<i class="fa-solid fa-globe text-surface-400"></i>
			<h3 class="font-semibold text-surface-800-200">{m.trustCenter()}</h3>
		</div>
		<label class="flex items-center gap-2 text-sm">
			<input type="checkbox" bind:checked={$settingsData.is_public} class="checkbox" />
			{m.makePublic()}
		</label>
		<p class="text-xs text-surface-500">{m.makePublicHelp()}</p>

		{#if $settingsData.is_public}
			<label class="flex items-center gap-2 text-sm">
				<input type="checkbox" bind:checked={$settingsData.is_primary} class="checkbox" />
				{m.primaryPortal()}
			</label>
			<p class="text-xs text-surface-500">{m.primaryPortalHelp()}</p>

			<div class="grid gap-4 sm:grid-cols-2">
				<label class="block text-sm">
					<span class="block text-surface-600-400">{m.tagline()}</span>
					<input bind:value={$settingsData.branding.tagline} class="input rounded-md" />
				</label>
				<label class="block text-sm">
					<span class="block text-surface-600-400">{m.logoUrl()}</span>
					<input
						bind:value={$settingsData.branding.logo_url}
						placeholder="https://…"
						class="input rounded-md"
					/>
				</label>
				<label class="block text-sm">
					<span class="block text-surface-600-400">{m.accentColor()}</span>
					<input
						type="color"
						value={$settingsData.branding.accent_color || '#7c3aed'}
						oninput={(e) => ($settingsData.branding.accent_color = e.currentTarget.value)}
						class="input h-10 rounded-md p-1"
					/>
				</label>
			</div>
		{/if}
	</div>

	<button class="btn preset-filled-primary-500">{m.save()}</button>
</form>

{#if portal.is_public && portal.public_token}
	<div class="card bg-surface-50-950 p-6 space-y-3 max-w-4xl mt-4">
		<h3 class="font-semibold text-surface-800-200">{m.publicLink()}</h3>
		<p class="text-xs text-surface-500">{m.publicLinkHelp()}</p>
		<div class="flex items-center gap-2">
			<input readonly value={publicUrl} class="input rounded-md text-sm grow font-mono" />
			<a
				href={`/trust/${portal.public_token}`}
				target="_blank"
				rel="noopener"
				class="btn btn-sm preset-tonal"
				aria-label={m.open()}><i class="fa-solid fa-arrow-up-right-from-square"></i></a
			>
			<button
				type="button"
				onclick={() => navigator.clipboard?.writeText(publicUrl)}
				class="btn btn-sm preset-tonal"
				aria-label={m.copy()}><i class="fa-solid fa-copy"></i></button
			>
		</div>
		<form method="POST" action="?/regeneratePublicToken" use:enhance={regenEnhance}>
			<button class="btn btn-sm preset-tonal-error">
				<i class="fa-solid fa-rotate mr-1"></i>{m.regenerateLink()}
			</button>
		</form>

		{#if portal.is_primary}
			<div class="border-t border-surface-200-800 pt-3">
				<p class="text-xs text-surface-500">{m.vanityUrlHelp()}</p>
				<div class="mt-2 flex items-center gap-2">
					<input
						readonly
						value={`${origin}/trust`}
						class="input rounded-md text-sm grow font-mono"
					/>
					<a
						href="/trust"
						target="_blank"
						rel="noopener"
						class="btn btn-sm preset-tonal"
						aria-label={m.open()}><i class="fa-solid fa-arrow-up-right-from-square"></i></a
					>
				</div>
			</div>
		{/if}
	</div>
{/if}
