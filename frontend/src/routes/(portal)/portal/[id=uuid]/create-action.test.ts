import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defaultWriteFormAction } from '#lib/utils/actions.js';
import { actions } from './+page.server';

vi.mock('#lib/utils/actions.js', async (importOriginal) => ({
	...(await importOriginal<typeof import('#lib/utils/actions.js')>()),
	defaultWriteFormAction: vi.fn(async () => ({}))
}));

type CreateEvent = Parameters<(typeof actions)['create']>[0];

function create(model: string): ReturnType<(typeof actions)['create']> {
	const url = new URL(`http://localhost/portal/p?/create&model=${encodeURIComponent(model)}`);
	return actions.create({ url } as unknown as CreateEvent);
}

describe('portal create action', () => {
	beforeEach(() => {
		vi.mocked(defaultWriteFormAction).mockClear();
	});

	it('creates an EBIOS RM study from a tile', async () => {
		await create('ebios-rm');
		expect(vi.mocked(defaultWriteFormAction)).toHaveBeenCalledWith(
			expect.objectContaining({ urlModel: 'ebios-rm', action: 'create' })
		);
	});

	it.each([
		['ebios-rm', true],
		['assets', false]
	])('opens the created %s only where the app does', async (model, opens) => {
		await create(model);
		expect(vi.mocked(defaultWriteFormAction)).toHaveBeenCalledWith(
			expect.objectContaining({ redirectToWrittenObject: opens })
		);
	});

	it.each([
		'not-a-model',
		'__proto__',
		'constructor',
		'toString',
		'',
		'ebios-rm_duplicate',
		'risk-assessment_duplicate',
		'applied-controls_duplicate'
	])('refuses %j', async (model) => {
		expect(await create(model)).toMatchObject({ status: 400 });
		expect(vi.mocked(defaultWriteFormAction)).not.toHaveBeenCalled();
	});
});
