import type { CellStyle, Sheet } from './types';

const ALIGN: Record<string, string> = {
	left: 'left',
	center: 'center',
	centerContinuous: 'center',
	right: 'right',
	justify: 'justify',
	distributed: 'justify',
	fill: 'left'
};

const VALIGN: Record<string, string> = {
	top: 'top',
	middle: 'middle',
	bottom: 'bottom',
	distributed: 'middle',
	justify: 'middle'
};

const ESCAPES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
const esc = (value: string) => value.replace(/[&<>"]/g, (c) => ESCAPES[c]);

const BASE_CSS = `
html{color-scheme:light}
body{margin:0;background:#fff}
table{border-collapse:collapse;table-layout:fixed;font:13px/1.45 system-ui,sans-serif;color:#111}
td{border:1px solid #e5e7eb;padding:2px 6px;vertical-align:bottom;overflow:hidden;text-overflow:ellipsis;white-space:pre}
td.frz{background:#fff}
`;

function declarations(style: CellStyle): string {
	const out: string[] = [];
	if (style.bg) out.push(`background:${style.bg}`);
	if (style.color) out.push(`color:${style.color}`);
	if (style.bold) out.push('font-weight:700');
	if (style.italic) out.push('font-style:italic');
	if (style.underline) out.push('text-decoration:underline');
	if (style.size) out.push(`font-size:${style.size}pt`);
	if (style.family && /^[\w\s-]+$/.test(style.family))
		out.push(`font-family:"${style.family}",sans-serif`);
	if (style.align && ALIGN[style.align]) out.push(`text-align:${ALIGN[style.align]}`);
	if (style.valign && VALIGN[style.valign]) out.push(`vertical-align:${VALIGN[style.valign]}`);
	if (style.wrap) out.push('white-space:pre-wrap;word-break:break-word');
	if (style.indent) out.push(`padding-left:${6 + style.indent * 8}px`);
	if (style.borders) {
		const [top, right, bottom, left] = style.borders;
		if (top) out.push(`border-top:${top}`);
		if (right) out.push(`border-right:${right}`);
		if (bottom) out.push(`border-bottom:${bottom}`);
		if (left) out.push(`border-left:${left}`);
	}
	return out.join(';');
}

function offsets(sizes: (number | undefined)[], fallback: number, count: number): number[] {
	const result: number[] = [];
	let total = 0;
	for (let i = 0; i < count; i++) {
		result.push(total);
		total += sizes[i] ?? fallback;
	}
	return result;
}

export function renderSheet(sheet: Sheet): { body: string; css: string } {
	const frozenRows = sheet.freeze?.rows ?? 0;
	const frozenCols = sheet.freeze?.cols ?? 0;
	const tops = offsets(
		sheet.heights.map((h) => (h ? Math.round(h * 1.34) : undefined)),
		20,
		frozenRows
	);
	const lefts = offsets(sheet.widths, 100, frozenCols);

	const rows = sheet.rows
		.map((cells, r) => {
			const height = sheet.heights[r];
			const tds = cells
				.map((cell, c) => {
					if (!cell) return '';
					const classes: string[] = [];
					const inline: string[] = [];
					if (r < frozenRows || c < frozenCols) {
						classes.push('frz');
						inline.push('position:sticky');
						if (r < frozenRows) inline.push(`top:${tops[r]}px`);
						if (c < frozenCols) inline.push(`left:${lefts[c]}px`);
						inline.push(`z-index:${r < frozenRows && c < frozenCols ? 3 : r < frozenRows ? 2 : 1}`);
					}
					if (cell.style !== undefined) classes.push(`s${cell.style}`);
					const attrs = [
						cell.rowspan ? ` rowspan="${cell.rowspan}"` : '',
						cell.colspan ? ` colspan="${cell.colspan}"` : '',
						classes.length ? ` class="${classes.join(' ')}"` : '',
						inline.length ? ` style="${inline.join(';')}"` : ''
					].join('');
					return `<td${attrs}>${esc(cell.text)}</td>`;
				})
				.join('');
			return `<tr${height ? ` style="height:${Math.round(height * 1.34)}px"` : ''}>${tds}</tr>`;
		})
		.join('');

	const colgroup = sheet.widths.map((w) => `<col style="width:${w}px">`).join('');
	return {
		body: `<table><colgroup>${colgroup}</colgroup><tbody>${rows}</tbody></table>`,
		css: BASE_CSS + sheet.styles.map((s, i) => `td.s${i}{${declarations(s)}}`).join('\n')
	};
}
