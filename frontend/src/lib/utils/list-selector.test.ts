import { describe, it, expect } from 'vitest';
import { filterOptions } from '#lib/utils/list-selector.js';

const chatSession = ['Assistant IA', "Conversation avec l'assistant IA"];

const options = [
	{
		label: 'permissionView',
		translatedLabel: 'Consulter',
		detail: 'view_chatsession',
		groupLabels: chatSession
	},
	{
		label: 'permissionAdd',
		translatedLabel: 'Ajouter',
		detail: 'add_chatsession',
		groupLabels: chatSession
	},
	{
		label: 'permissionView',
		translatedLabel: 'Consulter',
		detail: 'view_complianceassessment',
		groupLabels: ['Général', 'Audit']
	},
	{ label: 'Domain' }
];

const details = (found: { detail?: string }[]): (string | undefined)[] =>
	found.map((option) => option.detail);

describe('filterOptions', () => {
	it('keeps every option when the query is blank', () => {
		expect(filterOptions(options, '   ')).toEqual(options);
	});

	it('finds an option by its technical name', () => {
		expect(details(filterOptions(options, 'view_chatsession'))).toEqual(['view_chatsession']);
	});

	it('finds options by part of the technical name, ignoring case', () => {
		expect(details(filterOptions(options, 'CHATSESSION'))).toEqual([
			'view_chatsession',
			'add_chatsession'
		]);
	});

	it('finds options by their displayed label', () => {
		expect(details(filterOptions(options, 'ajout'))).toEqual(['add_chatsession']);
	});

	it('ignores the raw label when a translation is displayed', () => {
		expect(filterOptions(options, 'permission')).toEqual([]);
	});

	it('falls back to the raw label when there is no translation', () => {
		expect(filterOptions(options, 'domain')).toEqual([{ label: 'Domain' }]);
	});

	it('finds every option of a group by its heading', () => {
		expect(details(filterOptions(options, 'assistant ia'))).toEqual([
			'view_chatsession',
			'add_chatsession'
		]);
	});

	it('finds options by the heading of their model', () => {
		expect(details(filterOptions(options, 'AUDIT'))).toEqual(['view_complianceassessment']);
	});

	it('ignores spaces around the query', () => {
		expect(details(filterOptions(options, '  add_chat  '))).toEqual(['add_chatsession']);
	});
});
