// @vitest-environment node

import { render } from 'svelte/server';
import { expect, it } from 'vitest';
import Page from './+page.svelte';
import type { PageData } from './$types';

const data: Pick<PageData, 'portfolio' | 'denied'> = {
	denied: false,
	portfolio: {
		weights: {
			requirement_assessments: 2,
			risk_scenarios: 3,
			findings: 2,
			open_vulnerabilities: 2,
			data_breaches: 2,
			quantitative_risk_existing: 3
		},
		reference_controls: [],
		applied_controls: [
			{
				id: 'test-control',
				name: 'Access review',
				ref_id: 'AC-001',
				domain: 'Operations',
				priority: 2,
				can_edit_priority: true,
				score: 7,
				counts: {
					requirement_assessments: 2,
					audits: 1,
					risk_scenarios: 1,
					risk_treatment: 1,
					risk_existing: 1,
					findings: 0,
					evidences: 0,
					documents: 0,
					assets: 3,
					open_vulnerabilities: 0,
					resolved_vulnerabilities: 0,
					data_breaches: 0,
					incidents: 0,
					recurring_tasks: 0,
					threat_models: 0,
					security_exceptions: 1,
					quantitative_risk_existing: 0,
					quantitative_risk_added: 0,
					quantitative_risk_removed: 0
				}
			}
		]
	}
};

it('renders the ranked controls and risk link breakdown', () => {
	const { body } = render(Page, { props: { data } });
	expect(body).toContain('href="/applied-controls/test-control"');
	expect(body).toContain('Access review');
	expect(body).toContain('1 treatment · 1 existing');
	expect(body).toContain('By reference control');
});

it('shows the domain and inline priority editor for editable controls', () => {
	const { body } = render(Page, { props: { data } });
	expect(body).toContain('Operations');
	expect(body).toContain('aria-label="Priority for Access review"');
	expect(body).toContain('value="2" selected');
});

it('renders a ranked list with expandable relationship details instead of a wide table', () => {
	const { body } = render(Page, { props: { data } });
	expect(body).toContain('<ol');
	expect(body).not.toContain('<table');
	expect(body).toContain('Relationship breakdown');
	expect(body).toContain('Supporting links');
	expect(body).toContain('<dt>Assets</dt>');
	expect(body).toMatch(/1\s+security exception/);
	expect(body).toContain('Distinct audits');
});

it('shows the priority without an editor for read-only controls', () => {
	const portfolio = data.portfolio!;
	const { body } = render(Page, {
		props: {
			data: {
				...data,
				portfolio: {
					...portfolio,
					applied_controls: portfolio.applied_controls.map((row) => ({
						...row,
						can_edit_priority: false
					}))
				}
			}
		}
	});
	expect(body).toContain('P2');
	expect(body).not.toContain('aria-label="Priority for Access review"');
});

it('distinguishes an access denial from an empty portfolio', () => {
	const { body } = render(Page, { props: { data: { ...data, portfolio: null, denied: true } } });
	expect(body).toContain('You do not have access to control reliance.');
	expect(body).not.toContain('No visible controls');
});
