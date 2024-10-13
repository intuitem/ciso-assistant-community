<script lang="ts">
	export let title;
	export let desc;
	export let link;
	export let tags: string[] = [];
</script>

<article
	class="hover:animate-background rounded-xl bg-gradient-to-r from-green-300 via-blue-500 to-purple-600 p-0.5 shadow-xl transition hover:bg-[length:400%_400%] hover:shadow-sm hover:[animation-duration:_4s]"
>
	<div class="rounded-[10px] bg-white p-4 !pt-20 sm:p-6">
		<time datetime="2022-10-10" class="block text-xs text-gray-500"> {desc} </time>

		<a href={link}>
			<h3 class="mt-0.5 text-lg font-medium text-gray-900">
				{title}
			</h3>
		</a>

		<div class="mt-4 flex flex-wrap gap-1">
			{#each tags as tag}
				<span
					class="whitespace-nowrap rounded-full bg-purple-100 px-2.5 py-0.5 text-xs text-purple-600"
				>
					{tag}
				</span>
			{/each}
		</div>
	</div>
</article>

<style>
</style>
