<script lang="ts">
	import { onMount } from 'svelte';
	import { redirectToProvider } from '$lib/allauth.js';
	import Logo from '$lib/components/Logo/Logo.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// Mirrors the callback URL built by the "Login with SSO" button on /login:
	// the IdP callback lands on /sso/authenticate, which finalizes the session
	// and then forwards to `next`.
	function getSSOCallbackURL(callbackURL: string): string {
		const url = new URL(callbackURL);
		url.pathname = '/sso/authenticate';
		url.search = '';
		url.searchParams.set('next', data.next);
		return url.toString();
	}

	onMount(() => {
		redirectToProvider(
			data.SSOInfo.sp_entity_id,
			getSSOCallbackURL(data.SSOInfo.callback_url),
			'login'
		);
	});
</script>

<svelte:head>
	<title>CISO Assistant | {m.loginSSO()}</title>
</svelte:head>

<main class="h-screen bg-surface-200-800 flex flex-col items-center justify-center space-y-6">
	<div class="flex justify-center max-w-48">
		<Logo />
	</div>
	<div class="flex items-center space-x-3 text-surface-600-400">
		<i class="fa-solid fa-circle-notch fa-spin text-2xl"></i>
		<span>{m.loginSSO()}…</span>
	</div>
	<noscript>
		<a href="/login" class="anchor">{m.login()}</a>
	</noscript>
</main>
