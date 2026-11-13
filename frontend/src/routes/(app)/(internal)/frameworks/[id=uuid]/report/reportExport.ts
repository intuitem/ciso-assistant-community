export type Cell = string | number | null | undefined;

export type Sheet = { name: string; columns: string[]; rows: Cell[][] };

const SHEET_NAME_MAX = 31;

export async function downloadWorkbook(fileName: string, sheets: Sheet[]): Promise<void> {
	const { Workbook } = await import('exceljs');
	const workbook = new Workbook();
	for (const sheet of sheets) {
		const ws = workbook.addWorksheet(
			sheet.name.replace(/[\\/?*[\]:]/g, '-').slice(0, SHEET_NAME_MAX)
		);
		ws.addRow(sheet.columns);
		ws.getRow(1).font = { bold: true };
		for (const row of sheet.rows) ws.addRow(row.map((c) => c ?? ''));
		ws.columns.forEach((column, i) => {
			let longest = sheet.columns[i]?.length ?? 0;
			for (const r of sheet.rows) longest = Math.max(longest, String(r[i] ?? '').length);
			column.width = Math.min(Math.max(longest + 2, 8), 60);
		});
		ws.views = [{ state: 'frozen', ySplit: 1 }];
	}
	const buffer = await workbook.xlsx.writeBuffer();
	const url = URL.createObjectURL(
		new Blob([buffer], {
			type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		})
	);
	const link = document.createElement('a');
	link.href = url;
	link.download = fileName;
	link.click();
	URL.revokeObjectURL(url);
}
