<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		/** One keycap per key; `mod` renders ⌘ on Apple devices and Ctrl elsewhere. */
		keys: string[];
		class?: string;
	}

	let { keys, class: className = '' }: Props = $props();

	// The platform is only known in the browser: render invisibly until then so the
	// server-rendered "Ctrl" never flips to "⌘" in front of Mac users.
	let isApple: boolean | undefined = $state();
	onMount(() => {
		const platform =
			(navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData
				?.platform ||
			navigator.platform ||
			navigator.userAgent;
		isApple = /mac|iphone|ipad/i.test(platform);
	});

	const label = (key: string) => (key === 'mod' ? (isApple ? '⌘' : 'Ctrl') : key);
</script>

<span
	class="inline-flex items-center gap-0.5 transition-opacity {keys.includes('mod') &&
	isApple === undefined
		? 'opacity-0'
		: 'opacity-100'} {className}"
	dir="ltr"
	aria-hidden="true"
>
	{#each keys as key, i (i)}
		<kbd
			class="inline-flex h-5 min-w-5 items-center justify-center rounded-[5px] border border-surface-200-800 bg-surface-50-950 px-1 font-sans text-[11px] leading-none font-medium text-surface-600-400 shadow-[inset_0_-1px_0_var(--color-surface-200)] dark:shadow-[inset_0_-1px_0_var(--color-surface-800)]"
			>{label(key)}</kbd
		>
	{/each}
</span>
