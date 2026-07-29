import ExcelJS from 'exceljs';
import { describe, expect, it } from 'vitest';
import { parseCsv } from './parseCsv';
import { parseXlsx } from './parseXlsx';
import { renderSheet } from './renderSheet';

async function fixture(): Promise<ArrayBuffer> {
	const wb = new ExcelJS.Workbook();
	const ws = wb.addWorksheet('Risks');
	ws.columns = [{ width: 20 }, { width: 12 }, { width: 10 }];
	ws.mergeCells('A1:C1');
	ws.getCell('A1').value = 'Risk register <2026>';
	ws.getCell('A1').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF4F81BD' } };
	ws.getCell('A1').font = { bold: true, color: { argb: 'FFFFFFFF' }, size: 14 };
	ws.getCell('A2').value = new Date(Date.UTC(2026, 0, 15));
	ws.getCell('A2').numFmt = 'dd/mm/yyyy';
	ws.getCell('B2').value = 1234.5;
	ws.getCell('B2').numFmt = '#,##0.00';
	ws.getCell('C2').value = { formula: 'B2*2', result: 2469 } as never;
	ws.getCell('A3').value = 'themed';
	ws.getCell('A3').font = { color: { theme: 4 } } as never;
	ws.views = [{ state: 'frozen', xSplit: 0, ySplit: 1 }];
	wb.addWorksheet('Hidden', { state: 'hidden' });
	return (await wb.xlsx.writeBuffer()) as ArrayBuffer;
}

describe('parseXlsx', () => {
	it('keeps values, formats, merges, freeze panes and skips hidden sheets', async () => {
		const model = await parseXlsx(await fixture());
		expect(model.sheets).toHaveLength(1);
		expect(model.hiddenSheets).toBe(1);

		const sheet = model.sheets[0];
		expect(sheet.name).toBe('Risks');
		expect(sheet.freeze).toEqual({ rows: 1, cols: 0 });
		expect(sheet.rows[0][0]).toMatchObject({ text: 'Risk register <2026>', colspan: 3 });
		expect(sheet.rows[0][1]).toBeNull();
		expect(sheet.rows[1][0].text).toBe('15/01/2026');
		expect(sheet.rows[1][1].text).toBe('1,234.50');
		expect(sheet.rows[1][2].text).toBe('2469');
		expect(sheet.widths[0]).toBe(145);
	});

	it('maps fills, fonts and theme colours to validated hex', async () => {
		const sheet = (await parseXlsx(await fixture())).sheets[0];
		const title = sheet.styles[sheet.rows[0][0].style!];
		expect(title).toMatchObject({ bg: '#4f81bd', color: '#ffffff', bold: true, size: 14 });
		expect(sheet.styles[sheet.rows[2][0].style!].color).toBe('#4f81bd');
	});
});

describe('parseCsv', () => {
	it('handles quoted fields, embedded newlines and doubled quotes', () => {
		const buffer = new TextEncoder().encode('a,"b,1","say ""hi"""\n"multi\nline",x,y').buffer;
		const sheet = parseCsv(buffer as ArrayBuffer).sheets[0];
		expect(sheet.rows[0].map((c) => c!.text)).toEqual(['a', 'b,1', 'say "hi"']);
		expect(sheet.rows[1][0]!.text).toBe('multi\nline');
	});
});

describe('renderSheet', () => {
	it('escapes cell text and emits merges, widths and sticky freeze offsets', async () => {
		const sheet = (await parseXlsx(await fixture())).sheets[0];
		const { body, css } = renderSheet(sheet);
		expect(body).toContain('Risk register &lt;2026&gt;');
		expect(body).not.toContain('<2026>');
		expect(body).toContain('colspan="3"');
		expect(body).toContain('<col style="width:145px">');
		expect(body).toContain('position:sticky;top:0px');
		expect(css).toContain('background:#4f81bd');
	});

	it('lets a cell style win over the frozen-cell background fallback', async () => {
		const sheet = (await parseXlsx(await fixture())).sheets[0];
		const { css } = renderSheet(sheet);
		const frozen = css.indexOf('td.frz{background:#fff}');
		const styled = css.indexOf(`td.s${sheet.rows[0][0].style}{`);
		expect(frozen).toBeGreaterThan(-1);
		expect(styled).toBeGreaterThan(frozen);
	});

	it('drops font families that are not a plain name', () => {
		const { css } = renderSheet({
			name: 's',
			widths: [80],
			heights: [undefined],
			rows: [[{ text: 'x', style: 0 }]],
			styles: [{ family: 'Evil</style><script>alert(1)</script>' }],
			truncated: false
		});
		expect(css).not.toContain('</style>');
		expect(css).not.toContain('font-family');
	});
});
