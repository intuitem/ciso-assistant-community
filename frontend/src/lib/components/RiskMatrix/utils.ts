export type Level = {
	name: string;
	description: string;
	hexcolor: string;
};

export type RiskMatrixCell = {
	level: Level;
	row: number;
	col: number;
};

type RiskMatrix = RiskMatrixCell[][];

export function buildRiskMatrix(grid: number[][], levels: Level[]): RiskMatrix {
	return grid
		.map((row, i) =>
			row.map((cell, j) => ({
				level: levels[cell],
				row: i,
				col: j
			}))
		)
		.reverse();
}

export function reverseRows<T>(matrix: T[][]): T[][] {
	return matrix.slice().reverse();
}

export function reverseCols<T>(matrix: T[][]): T[][] {
	return matrix.map((row) => row.slice().reverse());
}

export function transpose<T>(matrix: T[][]): T[][] {
	if (!matrix || matrix.length === 0 || matrix[0].length === 0) {
		return [];
	}
	return reverseCols(
		reverseRows(matrix[0].map((_, colIndex) => matrix.map((row) => row[colIndex])))
	);
}
