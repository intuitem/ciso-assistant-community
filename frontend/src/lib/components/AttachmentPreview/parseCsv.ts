import type { SheetCell, SheetModel } from './types';

const MAX_ROWS = 2000;
const MAX_COLS = 100;

export function parseCsv(buffer: ArrayBuffer): SheetModel {
	const text = new TextDecoder('utf-8').decode(buffer).replace(/^\uFEFF/, '');
	const rows: string[][] = [];
	let row: string[] = [];
	let field = '';
	let quoted = false;
	for (let i = 0; i < text.length; i++) {
		const ch = text[i];
		if (quoted) {
			if (ch !== '"') field += ch;
			else if (text[i + 1] === '"') ((field += '"'), i++);
			else quoted = false;
		} else if (ch === '"') quoted = true;
		else if (ch === ',' || ch === ';' || ch === '\t') (row.push(field), (field = ''));
		else if (ch === '\n' || ch === '\r') {
			if (ch === '\r' && text[i + 1] === '\n') i++;
			row.push(field);
			rows.push(row);
			row = [];
			field = '';
		} else field += ch;
	}
	if (field || row.length) (row.push(field), rows.push(row));

	const truncated = rows.length > MAX_ROWS;
	const kept = rows.slice(0, MAX_ROWS);
	const colCount = Math.min(Math.max(0, ...kept.map((r) => r.length)), MAX_COLS);
	return {
		sheets: [
			{
				name: 'CSV',
				widths: Array(colCount).fill(120),
				heights: kept.map(() => undefined),
				rows: kept.map((r) =>
					Array.from({ length: colCount }, (_, c) => ({ text: r[c] ?? '' }) as SheetCell)
				),
				styles: [],
				truncated: truncated || kept.some((r) => r.length > MAX_COLS)
			}
		],
		hiddenSheets: 0
	};
}
