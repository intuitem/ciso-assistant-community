<script lang="ts">
	import { GraphLayoutType, GraphNodeShape } from '@unovis/ts';
	import GraphComponent from './OperatingModeGraph.svelte';

	import { m } from '$paraglide/messages';
	const data = {
		nodes: [
			{ id: 'blk-00', label: 'space is cool, really really cool', group: 'grp0', icon: '&#xf0c2;' },
			{ id: 'blk-03', label: 'this is nice', group: 'grp0', icon: '&#xe4e5;' },
			{
				id: 'blk-04',
				label: 'this is pretty',
				group: 'grp0',
				icon: '&#xf3cd;'
			},
			{
				id: 'blk-01',
				label: 'Ea ut fugiat ullamco deserunt et consequat adipisicing veniam sunt nulla sit qui.',
				group: 'grp0',
				icon: '&#xf233;'
			},
			{
				id: 'blk-02',
				label: 'Reconnaissance interne réseaux bureautique & IT site de Paris',
				group: 'grp1',
				icon: '&#xf1b3;'
			},
			{
				id: 'blk-022',
				label: 'Reconnaissance interne réseaux bureautique & IT site de Paris',
				group: 'grp1',
				icon: '&#xf6ff;'
			},
			{
				id: 'blk-023',
				group: 'grp11',
				icon: 'OR',
				size: 40,
				shape: GraphNodeShape.Circle
			},
			{ id: 'blk-11', label: 'short', group: 'grp2', icon: '&#xf1b2;' },
			{ id: 'blk-12', label: 'abc', group: 'grp3', icon: '&#xf15b;' },
			{
				id: 'blk-13',
				icon: '&#xf084;',
				label: "Création et maintien d'un canal d'exfiltration via un poste Internet",
				group: 'grp3'
			},
			{ id: 'blk-14', label: 'Vol et exploitation de données de R&D', group: 'grp3', icon: '💎' }
		],
		links: [
			{ source: 'blk-00', target: 'blk-02' },
			{ source: 'blk-01', target: 'blk-02' },
			{ source: 'blk-023', target: 'blk-11' },
			{ source: 'blk-11', target: 'blk-12' },
			{ source: 'blk-12', target: 'blk-13' },
			{ source: 'blk-13', target: 'blk-14' },
			{ source: 'blk-02', target: 'blk-023' },
			{ source: 'blk-022', target: 'blk-023' }
		]
	};

	const panelNodes = {
		reconnaissance: ['blk-00', 'blk-01', 'blk-03', 'blk-04'],
		initialAccess: ['blk-02', 'blk-022', 'blk-023'],
		discovery: ['blk-11'],
		exploitation: ['blk-12', 'blk-13', 'blk-14']
	};
</script>

<GraphComponent {data} {panelNodes} />
