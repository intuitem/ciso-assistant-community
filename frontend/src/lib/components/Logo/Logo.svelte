<script lang="ts">
	import ciso from '$lib/assets/ciso.svg';

	interface Props {
		height?: number;
		width?: number;
		variant?: 'icon' | 'full';
	}

	let { height = 200, width = 200, variant = 'icon' }: Props = $props();
</script>

{#if variant === 'full'}
	<div class="lockup" style:height="{height}px">
		<img class="c" height={height} width={height} src={ciso} alt="CISO TSI icon" data-testid="logo-image" />
		<span class="wordmark" style:font-size="{height * 0.34}px">CISO TSI</span>
	</div>
{:else}
	<img class="c" {height} {width} src={ciso} alt="CISO TSI icon" data-testid="logo-image" />
{/if}

<style>
	.lockup {
		display: flex;
		align-items: center;
		gap: 0.5em;
	}
	.wordmark {
		font-weight: 800;
		letter-spacing: -0.01em;
		color: var(--color-primary-500, #4b3fd6);
		white-space: nowrap;
	}
</style>
