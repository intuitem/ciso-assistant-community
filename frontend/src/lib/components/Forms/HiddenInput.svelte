<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';

	interface Props {
		field: string;
		form: any;
		[key: string]: any
	}

	let { field, form, ...rest }: Props = $props();

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
			{...rest}
		/>
	</div>
</div>
