import type { z } from 'zod';
import type { ModelMapEntry } from './crud';
import type { RiskScenarioSchema } from './schemas';

export interface User {
	id: string;
	email: string;
	first_name: string;
	last_name: string;
	is_active: boolean;
	date_joined: string;
}

export interface LoginRequestBody {
	username: string;
	password: string;
}

export const URL_MODEL = [
	'folders',
	'projects',
	'risk-matrices',
	'risk-assessments',
	'threats',
	'risk-scenarios',
	'security-measures',
	'policies',
	'risk-acceptances',
	'security-functions',
	'assets',
	'users',
	'user-groups',
	'roles',
	'role-assignments',
	'compliance-assessments',
	'evidences',
	'frameworks',
	'requirements',
	'requirement-assessments',
	'libraries'
] as const;

export type urlModel = (typeof URL_MODEL)[number];

export type ModelInfo = ModelMapEntry;

interface ProbabilityImpactItem {
	abbreviation: string;
	name: string;
	description: string;
}

interface RiskItem extends ProbabilityImpactItem {
	hexcolor: string;
}

export interface RiskMatrixJsonDefinition {
	name: string;
	description: string;
	probability: ProbabilityImpactItem[];
	impact: ProbabilityImpactItem[];
	risk: RiskItem[];
	grid: number[][];
}

export interface RiskMatrix {
	locale?: string; // optional, defaults en english.
	name: string;
	description: string;
	format_version?: string;
	json_definition: string; // stringified
}

export type RiskScenario = z.infer<typeof RiskScenarioSchema>;

interface LibraryObject {
	type: 'risk_matrix' | 'security_function' | 'threat';
	fields: Record<string, any>;
}

export interface Library {
	name: string;
	urn: string;
	id?: string;
	dependencies: string[];
	description: string;
	locale: 'en' | 'fr';
	format_version: string;
	objects: LibraryObject[];
	copyright: string;
	provider: string;
	packager: string;
}

export interface RiskLevel {
	current: string[];
	residual: string[];
}

export interface AggregatedData {
	names: string[];
}

export interface Counter {
	RiskAssessment: number;
	RiskScenario: number;
	SecurityMeasure: number;
	RiskAcceptance: number;
	Project: number;
}

export interface SecurityMeasureStatus {
	localLables: string[];
	labels: any[];
	values: any[]; // Set these types later on
}
