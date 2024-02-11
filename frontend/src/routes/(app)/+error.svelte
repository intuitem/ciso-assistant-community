<script>
	import { page } from '$app/stores';
</script>

<div class="container">
	<h1 class="status">Error {$page.status}</h1>
	<p class="message">{$page.error?.message}</p>
</div>

<style>
	.container {
		width: 100%;
		height: 100%;
		overflow: hidden;
	}
	.status {
		font-size: 6rem;
		margin: 6rem 0;
		text-align: center;
		font-weight: lighter;
	}
	.message {
		font-size: 3.3rem;
		text-align: center;
		font-weight: 600;
		padding: 0 1rem;
		line-height: 3.6rem;
	}
</style>
