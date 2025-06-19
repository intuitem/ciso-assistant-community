<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime';
	import { m } from '$paraglide/messages';
	import HalfGauge from './HalfGauge.svelte';

	let { audit } = $props();
	const badge_style = {
		planned: 'bg-yellow-100',
		in_progress: ' bg-orange-200',
		in_review: 'text-white bg-blue-500',
		done: 'text-white bg-cyan-600',
		deprecated: 'text-white bg-red-400',
		null: 'bg-gray-200'
	};
</script>

<div class="border-red-50 border rounded-tl-3xl rounded-br-2xl shadow-lg min-h-48">
	<div id="header" class="flex justify-end">
		<div
			class=" p-1 rounded-bl-lg text-sm font-semibold min-w-24 text-center {badge_style[
				audit.status
			]}"
		>
			{safeTranslate(audit.status) ?? '---'}
		</div>
	</div>
	<div id="body" class="grid grid-cols-6 px-2">
		<div id="progress" class="col-span-4">
			<div class="flex justify-center">
				<HalfGauge name={audit.id} value={audit.progress} />
			</div>
			<div class="flex justify-center pb-3">
				<a
					href="/compliance-assessments/{audit.id}"
					class="hover:text-violet-400 font-semibold text-center">{audit.name}</a
				>
			</div>
		</div>
		<div id="markers" class="col-span-2 grid grid-cols-1 gap-4 align-middle m-auto">
			<div class="text-xs">
				<span class="font-semibold">{m.framework()}: </span>{audit.framework.str}
			</div>
			<div class="text-xs">
				<span class="font-semibold">ETA: </span>{formatDateOrDateTime(audit.eta, getLocale()) ??
					'-'}
			</div>
		</div>
	</div>
</div>
