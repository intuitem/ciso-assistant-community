<script lang="ts">
	import * as m from '$paraglide/messages';
	import Tile from './Tile.svelte';
	const data = { ws1_1: [{ k: 'v' }, { k: 'v' }, { k: 'v' }] };
</script>

<div class="h-screen w-full p-8">
	<div class="card bg-white shadow-lg w-full h-full grid grid-cols-3 grid-rows-3 gap-8 p-8">
		<div class="border col-span-3 grid grid-cols-3 gap-4 p-4 bg-pink-600">
			<Tile title={m.ebiosWs1_1()} status="to_do" meta={data.ws1_1} />
			<Tile title={m.ebiosWs1_2()} status="in_progress" />
			<Tile title={m.ebiosWs1_3()} status="done" />
		</div>
		<div class="border bg-fuchsia-900 grid gap-4 p-4">
			<Tile title={m.ebiosWs2()} status="to_do" />
		</div>
		<div class="border col-span-2 grid grid-cols-2 gap-4 p-4 bg-teal-500">
			<Tile title={m.ebiosWs3_1()} status="to_do" />
			<Tile title={m.ebiosWs3_2()} status="done" />
		</div>
		<div class="border bg-yellow-600 grid gap-4 p-4">
			<Tile title={m.ebiosWs4()} status="in_progress" />
		</div>
		<div class="border bg-red-500 grid gap-4 p-4">
			<Tile title={m.ebiosWs5()} status="to_do" />
		</div>
		<div class="border bg-purple-800 grid gap-4 p-4">
			<Tile title={m.summary()} />
		</div>
	</div>
</div>
