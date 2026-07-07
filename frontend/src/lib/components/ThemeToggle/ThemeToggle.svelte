<script lang="ts">
	import { Switch } from '@skeletonlabs/skeleton-svelte';
	import { resolvedTheme, setTheme } from '$lib/utils/theme';
	import { m } from '$paraglide/messages';

	// A switch reads as "current state" (knob position), which sidesteps the
	// "describe state vs action" ambiguity of a single icon button. ON = dark.
	// The full Light/Dark/System choice (incl. following the OS) stays in settings.
	let isDark = $derived($resolvedTheme === 'dark');
</script>

<div class="flex items-center gap-1.5">
	<i class="fa-solid fa-sun text-xs {isDark ? 'text-surface-500' : 'text-warning-500'}"></i>
	<Switch
		name="theme-toggle"
		checked={isDark}
		onCheckedChange={(e) => setTheme(e.checked ? 'dark' : 'light')}
		data-testid="theme-toggle"
	>
		<Switch.Control>
			<Switch.Thumb />
		</Switch.Control>
		<Switch.HiddenInput />
	</Switch>
	<i class="fa-solid fa-moon text-xs {isDark ? 'text-primary-400' : 'text-surface-500'}"></i>
</div>
