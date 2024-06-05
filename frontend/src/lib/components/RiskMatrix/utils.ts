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
