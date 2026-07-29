export interface CellStyle {
	bg?: string;
	color?: string;
	bold?: boolean;
	italic?: boolean;
	underline?: boolean;
	size?: number;
	family?: string;
	align?: string;
	valign?: string;
	wrap?: boolean;
	indent?: number;
	borders?: (string | undefined)[];
}

export interface SheetCell {
	text: string;
	style?: number;
	rowspan?: number;
	colspan?: number;
}

export interface Sheet {
	name: string;
	widths: number[];
	heights: (number | undefined)[];
	rows: (SheetCell | null)[][];
	styles: CellStyle[];
	freeze?: { rows: number; cols: number };
	truncated: boolean;
}

export interface SheetModel {
	sheets: Sheet[];
	hiddenSheets: number;
}

export type WorkerRequest = { buffer: ArrayBuffer };
export type WorkerResponse = { ok: true; model: SheetModel } | { ok: false };
