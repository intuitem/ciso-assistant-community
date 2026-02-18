<script lang="ts">
	import { themeMode, setTheme, type ThemeMode } from '$lib/utils/theme';

	const modes: { value: ThemeMode; icon: string; label: string }[] = [
		{ value: 'light', icon: 'fa-sun', label: 'Light' },
		{ value: 'dark', icon: 'fa-moon', label: 'Dark' },
		{ value: 'system', icon: 'fa-desktop', label: 'System' }
	];

	function cycle() {
		const order: ThemeMode[] = ['light', 'dark', 'system'];
		const current = order.indexOf($themeMode);
		const next = order[(current + 1) % order.length];
		setTheme(next);
	}

	const currentMode = $derived(modes.find((m) => m.value === $themeMode) || modes[0]);
</script>

<button
	onclick={cycle}
	class="flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 text-surface-950-50 cursor-pointer"
	data-testid="theme-switch-button"
	aria-label="Toggle theme: {currentMode.label}"
>
	<i class="fa-solid {currentMode.icon} mr-2 w-4 text-center"></i>
	{currentMode.label}
</button>
