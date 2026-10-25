<script lang="ts">
	import { isDark } from '$lib/utils/helpers';

	interface Props {
		hexcolor: string;
		label: string;
		class?: string;
	}

	let { hexcolor, label, class: classes = '' }: Props = $props();
</script>

<!-- The background is a fixed hex color, so the text must be a fixed color too (not
theme-dependent), otherwise it turns light in dark mode and vanishes on a light
badge. White on dark backgrounds, fixed dark surface otherwise. -->
<p
	class="flex w-fit min-w-24 justify-center px-2 py-1 rounded-md whitespace-nowrap {isDark(hexcolor)
		? 'text-white'
		: 'text-surface-950'} {classes}"
	style="background-color: {hexcolor}"
>
	{label}
</p>
