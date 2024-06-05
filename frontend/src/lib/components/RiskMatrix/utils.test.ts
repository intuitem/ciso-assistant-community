import { buildRiskMatrix, type Level } from './utils';
import { describe, it, expect } from 'vitest';

describe('buildRiskMatrix', () => {
	it('should generate a risk matrix with the same dimensions as the input grid', () => {
		const grid = [
			[0, 1],
			[1, 0],
			[2, 2]
		];
		const levels = [{}, {}, {}] as Level[]; // Just placeholder objects for testing
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix.length).toBe(grid.length);
		risk_matrix.forEach((row, i) => {
			expect(row.length).toBe(grid[i].length);
		});
	});

	it('should map grid values to levels', () => {
		const grid = [
			[0, 1],
			[2, 3]
		];
		const levels = [{ name: 'L0' }, { name: 'L1' }, { name: 'L2' }, { name: 'L3' }] as Level[];
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix[0][0].level).toBe(levels[2]); // Note the reversed order of rows
		expect(risk_matrix[0][1].level).toBe(levels[3]);
		expect(risk_matrix[1][0].level).toBe(levels[0]);
		expect(risk_matrix[1][1].level).toBe(levels[1]);
	});

	it('should reverse the order of rows', () => {
		const grid = [
			[0, 1],
			[2, 3]
		];
		const levels = [{ name: 'L0' }, { name: 'L1' }, { name: 'L2' }, { name: 'L3' }] as Level[];
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix[0][0].level).toBe(levels[2]);
		expect(risk_matrix[1][0].level).toBe(levels[0]);
	});

	it('should set correct row and col properties for each cell', () => {
		const grid = [
			[0, 1],
			[1, 0]
		];
		const levels = [{}, {}] as Level[]; // Just placeholder objects for testing
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix[0][0].row).toBe(1); // Note the reversed order of rows
		expect(risk_matrix[0][0].col).toBe(0);

		expect(risk_matrix[0][1].row).toBe(1);
		expect(risk_matrix[0][1].col).toBe(1);

		expect(risk_matrix[1][0].row).toBe(0);
		expect(risk_matrix[1][0].col).toBe(0);

		expect(risk_matrix[1][1].row).toBe(0);
		expect(risk_matrix[1][1].col).toBe(1);
	});
});

describe('buildRiskMatrix failing tests', () => {
	it('should fail if risk matrix dimensions mismatch', () => {
		const grid = [
			[0, 1],
			[1, 0]
		];
		const levels = [{}, {}] as Level[];
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix.length).not.toBe(3); // This is wrong, should be 2
	});

	it('should fail if levels are mapped incorrectly', () => {
		const grid = [
			[0, 1],
			[2, 3]
		];
		const levels = [{ name: 'L0' }, { name: 'L1' }, { name: 'L2' }, { name: 'L3' }] as Level[];
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix[0][0].level).not.toBe(levels[3]); // This is wrong, should be levels[2]
	});

	it('should fail if rows are not reversed', () => {
		const grid = [
			[0, 1],
			[2, 3]
		];
		const levels = [{ name: 'L0' }, { name: 'L1' }, { name: 'L2' }, { name: 'L3' }] as Level[];
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix[0][0].level).not.toBe(levels[0]); // This is wrong, should be levels[2]
	});

	it('should fail if row and col properties are incorrect', () => {
		const grid = [
			[0, 1],
			[1, 0]
		];
		const levels = [{}, {}] as Level[];
		const risk_matrix = buildRiskMatrix(grid, levels);

		expect(risk_matrix[0][0].row).not.toBe(0); // This is wrong, should be 1
		expect(risk_matrix[0][0].col).not.toBe(1); // This is wrong, should be 0
	});
});
