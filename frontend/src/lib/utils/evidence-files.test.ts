import { describe, expect, it } from 'vitest';
import { superValidate } from 'sveltekit-superforms/server';
import { zod4 } from 'sveltekit-superforms/adapters';
import { EvidenceSchema, EvidenceRevisionSchema } from './schemas';
import { evidenceFileDisplay, evidenceMultipart, mergeEvidenceFiles } from './evidence-files';

describe('evidence multipart form submission', () => {
	it('keeps ten selected files through form validation', async () => {
		const form = new FormData();
		form.set('name', 'Proof');
		form.set('folder', '6da5a1ad-e8ef-4a05-bcac-67282e71f955');
		for (let i = 0; i < 10; i++) form.append('attachments', new File([String(i)], `${i}.txt`));
		const parsed = await superValidate(form, zod4(EvidenceSchema));
		expect(parsed.valid).toBe(true);
		expect(parsed.data.attachments).toHaveLength(10);
		expect(parsed.data.attachments?.map((file: File) => file.name)).toEqual(
			Array.from({ length: 10 }, (_, i) => `${i}.txt`)
		);
	});
	it('rejects eleven files in both evidence and revision forms', async () => {
		for (const schema of [EvidenceSchema, EvidenceRevisionSchema]) {
			const parsed = await superValidate(
				{ attachments: Array.from({ length: 11 }, () => new File(['x'], 'x.txt')) },
				zod4(schema)
			);
			expect(parsed.valid).toBe(false);
			expect(parsed.errors.attachments).toBeDefined();
		}
	});
	it('preserves empty relations, nulls and duplicate filenames in one upload', () => {
		const metadata = { name: 'Proof', owner: [], task_node: null, status: 'draft' };
		const body = evidenceMultipart(metadata, [
			new File(['a'], 'same.txt'),
			new File(['b'], 'same.txt')
		]);
		expect(JSON.parse(body.get('payload') as string)).toEqual(metadata);
		expect(body.getAll('attachments')).toHaveLength(2);
		expect(
			body.getAll('attachments').every((file) => file instanceof File && file.name === 'same.txt')
		).toBe(true);
	});

	it('keeps previous files when the picker is used repeatedly', () => {
		const first = new File(['first'], 'first.txt');
		const second = new File(['second'], 'second.txt');
		const repeated = new File(['first again'], 'first.txt');
		expect(mergeEvidenceFiles([first], [second, repeated])).toEqual([first, second, repeated]);
	});

	it('shows every file of a revision with its own size', () => {
		expect(
			evidenceFileDisplay([
				{ filename: 'audit.pdf', size: '112.7 KB' },
				{ filename: 'report.docx', size: '395.4 KB' }
			])
		).toEqual([
			{ filename: 'audit.pdf', size: '112.7 KB' },
			{ filename: 'report.docx', size: '395.4 KB' }
		]);
	});

	it('still renders a legacy single-file value', () => {
		expect(evidenceFileDisplay('legacy.pdf')).toEqual([{ filename: 'legacy.pdf', size: null }]);
	});
});
