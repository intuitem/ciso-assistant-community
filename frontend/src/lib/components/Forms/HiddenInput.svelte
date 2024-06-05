<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';

	export let field: string;
	export let form;

	const { value, constraints } = formFieldProxy(form, field);
</script>

<div>
	<div class="control">
		<input
			hidden
			name={field}
			placeholder=""
			bind:value={$value}
			{...$constraints}
			{...$$restProps}
		/>
	</div>
</div>
