import type { IExecuteFunctions, IDataObject } from "n8n-workflow";

/**
 * Credentials interface for CISO Assistant API
 */
export interface ICisoAssistantCredentials {
  patKey: string;
  baseUrl: string;
  skipTLS: boolean;
}

/**
 * Base request configuration
 */
export interface IRequestConfig {
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  url: string;
  body?: IDataObject;
  headers?: IDataObject;
}

/**
 * Resource handler context
 */
export interface IResourceContext {
  executeFunctions: IExecuteFunctions;
  credentials: ICisoAssistantCredentials;
  itemIndex: number;
}

/**
 * Base resource handler interface
 */
export interface IResourceHandler {
  execute(operation: string, context: IResourceContext): Promise<IDataObject>;
}

/**
 * Resource registry entry
 */
export interface IResourceRegistryEntry {
  name: string;
  handler: new () => IResourceHandler;
}

/**
 * Common response types
 */
export interface IPaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: IDataObject[];
}

/**
 * Resource types supported by CISO Assistant
 */
export type ResourceType =
  | "system"
  | "domain"
  | "perimeter"
  | "asset"
  | "audit"
  | "riskAssessment"
  | "incident"
  | "vulnerability"
  | "appliedControl"
  | "taskOccurrence"
  | "taskDefinition"
  | "findingsAssessment"
  | "finding"
  | "securityException"
  | "evidence"
  | "entity"
  | "solution"
  | "representative"
  | "entityAssessment"
  | "rightRequest"
  | "dataBreach"
  | "riskScenario"
  | "riskMatrix"
  | "framework";

/**
 * Common CRUD operations
 */
export type CRUDOperation =
  | "create"
  | "getByName"
  | "getByRefId"
  | "list"
  | "update"
  | "delete";

/**
 * Special operations
 */
export type SpecialOperation =
  | "getBuildInfo"
  | "getUsers"
  | "updateRequirementAssessment"
  | "createRevision"
  | "getRevisions";

export type Operation = CRUDOperation | SpecialOperation;
