import { TYPE_META } from './universe';
import type { EgoGraph, EgoNode } from './ego';

const SIZE = [40, 22, 15, 11];

function nodeSize(n: EgoNode): number {
	if (n.aggregate) return 13;
	return SIZE[Math.min(n.depth, SIZE.length - 1)];
}

function truncate(s: string, n: number): string {
	return s.length <= n ? s : s.slice(0, n - 1) + '…';
}

function esc(s: string): string {
	return String(s).replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c]!);
}

function labelSide(n: EgoNode): 'left' | 'right' | 'top' | 'bottom' {
	const a = (Math.atan2(n.y, n.x) * 180) / Math.PI;
	if (a > 75 && a < 105) return 'bottom';
	if (a < -75 && a > -105) return 'top';
	return Math.abs(a) > 90 ? 'left' : 'right';
}

export interface OptionParams {
	graph: EgoGraph;
	mode: 'radial' | 'force';
	showLabels: boolean;
	dark: boolean;
}

export function buildGraphOption({ graph, mode, showLabels, dark }: OptionParams) {
	const byId = new Map(graph.nodes.map((n) => [n.id, n]));
	const dim = dark ? '#94a3b8' : '#64748b';

	const data = graph.nodes.map((n) => {
		const meta = TYPE_META[n.type];
		const isRoot = n.depth === 0;
		return {
			id: n.id,
			name: n.name,
			x: n.x,
			y: n.y,
			fixed: mode === 'force' ? isRoot : undefined,
			symbol: n.aggregate ? 'circle' : meta.symbol,
			symbolSize: nodeSize(n),
			itemStyle: {
				color: n.aggregate ? 'transparent' : meta.color,
				opacity: n.aggregate ? 1 : Math.max(0.45, 1 - n.depth * 0.18),
				borderColor: n.aggregate ? meta.color : isRoot ? (dark ? '#fff' : '#1e293b') : 'transparent',
				borderWidth: n.aggregate ? 1.5 : isRoot ? 3 : 0,
				borderType: n.aggregate ? [3, 2] : 'solid'
			},
			label: {
				show: showLabels && (isRoot || n.depth <= 1 || !!n.aggregate),
				// Labels read outwards from the centre, otherwise the left half of the
				// ring writes its text back over the graph.
				position: isRoot ? 'bottom' : labelSide(n),
				distance: isRoot ? 10 : 6,
				fontSize: isRoot ? 12 : 10,
				fontWeight: isRoot ? 'bold' : 'normal',
				color: dark ? '#e2e8f0' : '#334155',
				formatter: () =>
					n.aggregate ? n.name : isRoot ? truncate(n.name, 44) : (n.meta?.ref ?? truncate(n.name, 14))
			}
		};
	});

	const links = graph.links.map((l) => ({
		source: l.source,
		target: l.target,
		value: l.verb,
		lineStyle: {
			color: dim,
			opacity: Math.max(0.15, 0.5 - (l.depth - 1) * 0.12),
			width: l.depth <= 1 ? 1.6 : 1,
			curveness: 0.12
		}
	}));

	return {
		animationDuration: 400,
		animationEasingUpdate: 'quinticInOut',
		tooltip: {
			trigger: 'item',
			confine: true,
			backgroundColor: dark ? 'rgba(15,23,42,0.96)' : 'rgba(255,255,255,0.97)',
			borderColor: dark ? '#334155' : '#cbd5e1',
			textStyle: { color: dark ? '#e2e8f0' : '#1e293b', fontSize: 12 },
			formatter: (p: any) => {
				if (p.dataType === 'edge') {
					const s = byId.get(p.data.source);
					const t = byId.get(p.data.target);
					return `<span style="opacity:.7">${esc(s?.name ?? '')}</span><br/><b>${esc(p.data.value)}</b><br/><span style="opacity:.7">${esc(t?.name ?? '')}</span>`;
				}
				const n = byId.get(p.data.id);
				if (!n) return '';
				if (n.aggregate) {
					return `<b>${n.aggregate.count} more ${TYPE_META[n.aggregate.type].label.toLowerCase()}(s)</b><br/><span style="opacity:.7">click to expand</span>`;
				}
				const meta = TYPE_META[n.type];
				const rows = Object.entries(n.meta ?? {})
					.map(
						([k, v]) =>
							`<tr><td style="opacity:.6;padding-right:8px">${esc(k)}</td><td>${esc(v)}</td></tr>`
					)
					.join('');
				return `<div style="max-width:260px">
					<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${meta.color};margin-right:6px"></span>
					<span style="font-size:11px;opacity:.7">${meta.label}</span>
					<div style="font-weight:600;margin:2px 0 4px;white-space:normal">${esc(n.name)}</div>
					<table style="font-size:11px">${rows}</table>
					<div style="font-size:10px;opacity:.55;margin-top:6px">click to re-centre · double-click to open</div>
				</div>`;
			}
		},
		series: [
			{
				type: 'graph',
				layout: mode === 'force' ? 'force' : 'none',
				// ECharts fits the node bounding box, not the labels hanging off it.
				zoom: mode === 'force' ? 1 : 0.86,
				roam: true,
				draggable: true,
				data,
				links,
				edgeSymbol: ['none', 'arrow'],
				edgeSymbolSize: 6,
				force: { repulsion: 260, edgeLength: [60, 130], gravity: 0.08, friction: 0.15 },
				emphasis: {
					focus: 'adjacency',
					scale: 1.1,
					label: { show: true },
					edgeLabel: {
						show: true,
						formatter: (p: any) => p.data.value,
						fontSize: 10,
						color: dark ? '#cbd5e1' : '#475569',
						backgroundColor: dark ? 'rgba(15,23,42,.85)' : 'rgba(255,255,255,.9)',
						padding: [2, 4]
					}
				},
				blur: {
					itemStyle: { opacity: 0.12 },
					lineStyle: { opacity: 0.05 },
					label: { opacity: 0.15 }
				},
				labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
				lineStyle: { color: dim }
			}
		]
	};
}
