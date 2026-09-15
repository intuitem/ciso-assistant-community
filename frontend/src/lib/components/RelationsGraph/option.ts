import { metaFor } from './meta';
import { canExpand, type LiveGraph, type LiveNode } from './accretion';

function truncate(s: string, n: number): string {
	return s.length <= n ? s : s.slice(0, n - 1) + '…';
}

function esc(s: string): string {
	return String(s).replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' })[c]!);
}

/** ref_id is the label when it is genuinely short; some models put a full identifier there. */
const MAX_REF = 16;

export function shortLabel(n: LiveNode): string {
	if (n.aggregate) return n.name;
	const ref = n.ref?.trim();
	if (ref && ref.length <= MAX_REF) return ref;
	return truncate(n.name, 14);
}

function labelSide(n: LiveNode): 'left' | 'right' | 'top' | 'bottom' {
	const a = (Math.atan2(n.y, n.x) * 180) / Math.PI;
	if (a > 75 && a < 105) return 'bottom';
	if (a < -75 && a > -105) return 'top';
	return Math.abs(a) > 90 ? 'left' : 'right';
}

export function buildGraphOption(graph: LiveGraph, showLabels: boolean, dark: boolean) {
	const nodes = [...graph.nodes.values()];
	const byId = graph.nodes;
	const dim = dark ? '#94a3b8' : '#64748b';

	const data = nodes.map((n) => {
		const meta = metaFor(n.urlModel);
		const isRoot = n.hop === 0;
		// Halo = more behind it; flat = fully expanded; faded = at the hop limit.
		const hasMore = canExpand(n);
		return {
			id: n.id,
			name: n.name,
			x: n.x,
			y: n.y,
			symbol: n.aggregate ? 'circle' : meta.symbol,
			symbolSize: isRoot ? 38 : n.aggregate ? 13 : Math.max(13, 22 - n.hop * 3),
			itemStyle: {
				color: n.aggregate ? 'transparent' : meta.color,
				opacity: n.frontier ? 0.45 : n.expanded ? 0.75 : 1,
				borderColor: n.aggregate
					? meta.color
					: isRoot
						? dark
							? '#fff'
							: '#1e293b'
						: n.loading
							? dark
								? '#fff'
								: '#1e293b'
							: hasMore
								? meta.color
								: 'transparent',
				borderWidth: n.aggregate ? 1.5 : isRoot ? 3 : n.loading ? 3 : hasMore ? 4 : 0,
				borderType: n.aggregate || n.loading ? [3, 2] : 'solid'
			},
			label: {
				show: showLabels,
				position: isRoot ? 'bottom' : labelSide(n),
				distance: isRoot ? 10 : 6,
				fontSize: isRoot ? 12 : 10,
				fontWeight: isRoot ? 'bold' : 'normal',
				color: dark ? '#e2e8f0' : '#334155',
				formatter: () => (isRoot ? truncate(n.name, 40) : shortLabel(n))
			}
		};
	});

	const links = [...graph.edges.values()].map((l) => ({
		source: l.source,
		target: l.target,
		value: l.verb,
		lineStyle: { color: dim, opacity: 0.45, width: 1.4, curveness: 0.1 }
	}));

	return {
		animationDuration: 400,
		animationDurationUpdate: 500,
		animationEasingUpdate: 'cubicOut',
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
				const meta = metaFor(n.urlModel);
				if (n.aggregate) {
					return `<b>${n.aggregate.count} more</b><br/><span style="opacity:.7">click to show them</span>`;
				}
				const rows = Object.entries(n.meta ?? {})
					.map(
						([k, v]) =>
							`<tr><td style="opacity:.6;padding-right:8px">${esc(k)}</td><td>${esc(v)}</td></tr>`
					)
					.join('');
				const hint = n.loading
					? 'loading…'
					: n.expanded
						? 'click to collapse'
						: n.frontier
							? 'edge of this view — open it to explore from there'
							: canExpand(n)
								? 'click to expand'
								: 'nothing further';
				return `<div style="max-width:260px">
					<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${meta.color};margin-right:6px"></span>
					<span style="font-size:11px;opacity:.7">${meta.label}</span>
					<div style="font-weight:600;margin:2px 0 4px;white-space:normal">${esc(n.name)}</div>
					<table style="font-size:11px">${rows}</table>
					<div style="font-size:10px;opacity:.55;margin-top:6px">${hint}</div>
				</div>`;
			}
		},
		series: [
			{
				type: 'graph',
				layout: 'none',
				// ECharts fits the nodes, not the labels hanging off them.
				zoom: 0.86,
				roam: true,
				draggable: true,
				data,
				links,
				edgeSymbol: ['none', 'arrow'],
				edgeSymbolSize: 6,
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
