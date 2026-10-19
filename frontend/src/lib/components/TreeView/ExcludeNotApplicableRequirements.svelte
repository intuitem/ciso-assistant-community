<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		excludeNotApplicableRequirements: boolean;
	}

	let { excludeNotApplicableRequirements = $bindable(false) }: Props = $props();
</script>

<button
	type="button"
	class="btn btn-sm preset-tonal"
	onclick={() => {
		excludeNotApplicableRequirements = !excludeNotApplicableRequirements;
	}}
>
	<i class="fa-solid {excludeNotApplicableRequirements ? 'fa-plus' : 'fa-minus'} text-xs"></i>
	<span class="text-xs"
		>{excludeNotApplicableRequirements
			? m.includeNotApplicableRequirements()
			: m.excludeNotApplicableRequirements()}</span
	>
</button>
