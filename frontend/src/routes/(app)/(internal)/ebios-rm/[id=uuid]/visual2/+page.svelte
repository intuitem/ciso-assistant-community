<script>
	import { writable } from 'svelte/store';
	import { SvelteFlow, Background, Controls, MiniMap } from '@xyflow/svelte';

	import '@xyflow/svelte/dist/style.css';

	const nodes = writable([
		{
			id: 'roto:123',
			type: 'group',
			position: { x: 50, y: 50 },
			style: 'width: 450px; height:450px;'
		},
		{
			id: 'study_scope',
			type: 'group',
			position: { x: 400, y: 400 },
			style: 'width: 350px; height:450px;'
		},
		{
			id: '1', // required and needs to be a string
			position: { x: 10, y: 10 }, // required
			data: { label: 'Activiste' }, // required
			parentId: 'roto:123',
			extent: 'parent'
		},
		{
			id: '2',
			position: { x: 200, y: 200 },
			data: {
				label:
					'Saboter la prochaine campagne nationale de vaccination en perturbant la production ou la distribution des vaccins, pour générer un choc psychologique sur la population et discréditer les pouvoirs publics.'
			},
			style: 'width: 250px;',
			parentId: 'roto:123',
			extent: 'parent'
		},
		{
			id: '3',
			position: { x: 300, y: 300 },
			data: {
				label:
					'Perte ou destruction des informations d’études et recherches conduisant à un fort impact, notamment sur les futures autorisations de mises sur le marché de l’entreprise'
			}
		}
	]);
	const edges = writable([
		{ id: 'e1-2', source: '1', target: '2', label: 'aims to' },
		{ id: 'e1-3', source: '1', target: '3', label: 'generates' }
	]);
	const snapGrid = [20, 20];
</script>

<main class="card bg-white">
	<SvelteFlow {nodes} {edges} {snapGrid} fitViewproOptions={{ hideAttribution: true }}>
		<Background bgColor="#fffff0" />
		<Controls />
		<MiniMap />
	</SvelteFlow>
</main>

<style>
	main {
		height: 80vh;
	}
</style>
