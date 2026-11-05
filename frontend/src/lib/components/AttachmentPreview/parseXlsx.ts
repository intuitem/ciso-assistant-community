import SSF from 'ssf';
import { Workbook } from 'exceljs';
import type { CellStyle, Sheet, SheetCell, SheetModel } from './types';

const MAX_SHEETS = 50;
const MAX_ROWS = 2000;
const MAX_COLS = 100;
const EPOCH = Date.UTC(1899, 11, 30);

const THEME = [
	'ffffff',
	'000000',
	'eeece1',
	'1f497d',
	'4f81bd',
	'c0504d',
	'9bbb59',
	'8064a2',
	'4bacc6',
	'f79646',
	'0000ff',
	'800080'
];

const BORDER_WIDTH: Record<string, string> = {
	thin: '1px solid',
	hair: '1px solid',
	medium: '2px solid',
	thick: '3px solid',
	double: '3px double',
	dashed: '1px dashed',
	dotted: '1px dotted',
	dashDot: '1px dashed',
	dashDotDot: '1px dotted',
	mediumDashed: '2px dashed',
	mediumDashDot: '2px dashed',
	mediumDashDotDot: '2px dotted',
	slantDashDot: '2px dashed'
};

function tinted(hex: string, tint: number): string {
	if (!tint) return `#${hex}`;
	const channel = (i: number) => {
		const c = parseInt(hex.slice(i, i + 2), 16);
		const v = tint > 0 ? c + (255 - c) * tint : c * (1 + tint);
		return Math.max(0, Math.min(255, Math.round(v)))
			.toString(16)
			.padStart(2, '0');
	};
	return `#${channel(0)}${channel(2)}${channel(4)}`;
}

function color(c: any): string | undefined {
	if (!c) return undefined;
	if (typeof c.argb === 'string') {
		const hex = c.argb.length === 8 ? c.argb.slice(2) : c.argb;
		return /^[0-9a-f]{6}$/i.test(hex) ? `#${hex.toLowerCase()}` : undefined;
	}
	if (typeof c.theme === 'number' && THEME[c.theme]) return tinted(THEME[c.theme], c.tint ?? 0);
	return undefined;
}

function edge(b: any): string | undefined {
	if (!b?.style) return undefined;
	const width = Object.hasOwn(BORDER_WIDTH, b.style) ? BORDER_WIDTH[b.style] : '1px solid';
	return `${width} ${color(b.color) ?? '#9ca3af'}`;
}

function styleOf(cell: any): CellStyle | undefined {
	const s: CellStyle = {};
	const font = cell.font;
	if (font) {
		if (font.bold) s.bold = true;
		if (font.italic) s.italic = true;
		if (font.underline) s.underline = true;
		if (font.size) s.size = font.size;
		if (font.name) s.family = font.name;
		const c = color(font.color);
		if (c) s.color = c;
	}
	if (cell.fill?.type === 'pattern' && cell.fill.pattern !== 'none') {
		const c = color(cell.fill.fgColor);
		if (c) s.bg = c;
	}
	const align = cell.alignment;
	if (align) {
		if (align.horizontal) s.align = align.horizontal;
		if (align.vertical) s.valign = align.vertical;
		if (align.wrapText) s.wrap = true;
		if (align.indent) s.indent = align.indent;
	}
	const b = cell.border;
	if (b) {
		const borders = [edge(b.top), edge(b.right), edge(b.bottom), edge(b.left)];
		if (borders.some(Boolean)) s.borders = borders;
	}
	return Object.keys(s).length ? s : undefined;
}

function formatted(numFmt: string | undefined, value: any): string {
	if (value instanceof Date) {
		const serial = (value.getTime() - EPOCH) / 86400000;
		try {
			return SSF.format(numFmt || 'yyyy-mm-dd', serial);
		} catch {
			return value.toISOString().slice(0, 10);
		}
	}
	if (typeof value === 'number') {
		if (!numFmt || numFmt === 'General') return String(value);
		try {
			return SSF.format(numFmt, value);
		} catch {
			return String(value);
		}
	}
	return String(value ?? '');
}

function textOf(value: any, numFmt: string | undefined): string {
	if (value == null) return '';
	if (value instanceof Date) return formatted(numFmt, value);
	if (typeof value === 'object') {
		if (Array.isArray(value.richText)) return value.richText.map((r: any) => r.text).join('');
		if ('result' in value) return textOf(value.result, numFmt);
		if ('text' in value) return String(value.text);
		if ('error' in value) return String(value.error);
		return '';
	}
	return formatted(numFmt, value);
}

function styleIndexer(styles: CellStyle[]) {
	const seen = new Map<string, number>();
	return (style: CellStyle | undefined) => {
		if (!style) return undefined;
		const key = JSON.stringify(style);
		let index = seen.get(key);
		if (index === undefined) {
			index = styles.push(style) - 1;
			seen.set(key, index);
		}
		return index;
	};
}

function readSheet(ws: any): Sheet {
	const styles: CellStyle[] = [];
	const indexOf = styleIndexer(styles);
	const rowCount = Math.min(ws.rowCount || 0, MAX_ROWS);
	const colCount = Math.min(ws.columnCount || 0, MAX_COLS);
	const truncated = (ws.rowCount || 0) > MAX_ROWS || (ws.columnCount || 0) > MAX_COLS;

	const spans = new Map<string, [number, number]>();
	for (const merge of Object.values<any>(ws._merges ?? {})) {
		spans.set(merge.tl, [merge.bottom - merge.top + 1, merge.right - merge.left + 1]);
	}

	const rows: (SheetCell | null)[][] = [];
	const heights: (number | undefined)[] = [];
	for (let r = 1; r <= rowCount; r++) {
		const row = ws.getRow(r);
		heights.push(row.height);
		const cells: (SheetCell | null)[] = [];
		for (let c = 1; c <= colCount; c++) {
			const cell = row.getCell(c);
			if (cell.isMerged && cell.master?.address !== cell.address) {
				cells.push(null);
				continue;
			}
			const out: SheetCell = { text: textOf(cell.value, cell.numFmt) };
			const style = indexOf(styleOf(cell));
			if (style !== undefined) out.style = style;
			const span = spans.get(cell.address);
			if (span) {
				if (span[0] > 1) out.rowspan = span[0];
				if (span[1] > 1) out.colspan = span[1];
			}
			cells.push(out);
		}
		rows.push(cells);
	}

	const widths: number[] = [];
	for (let c = 1; c <= colCount; c++) {
		const width = ws.getColumn(c)?.width;
		widths.push(Math.round((width ?? 9) * 7 + 5));
	}

	const view = (ws.views ?? [])[0];
	const freeze =
		view?.state === 'frozen' && (view.xSplit || view.ySplit)
			? { rows: Math.min(view.ySplit ?? 0, rowCount), cols: Math.min(view.xSplit ?? 0, colCount) }
			: undefined;

	return { name: ws.name, widths, heights, rows, styles, freeze, truncated };
}

export async function parseXlsx(buffer: ArrayBuffer): Promise<SheetModel> {
	const wb = new Workbook();
	await wb.xlsx.load(buffer);
	const visible = wb.worksheets.filter(
		(ws: any) => ws.state !== 'hidden' && ws.state !== 'veryHidden'
	);
	const kept = visible.slice(0, MAX_SHEETS);
	return {
		sheets: kept.map(readSheet),
		omittedSheets: wb.worksheets.length - kept.length
	};
}
