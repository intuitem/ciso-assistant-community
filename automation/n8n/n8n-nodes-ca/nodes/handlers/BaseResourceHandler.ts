import type { IDataObject } from "n8n-workflow";
import type { IResourceHandler, IResourceContext } from "../types";
import { makeRequest, buildUrl, buildFilterParams } from "../utils/http";
import { buildRequestBody, buildUpdateBody } from "../utils/validation";
import { handleOperationError } from "../utils/errors";

/**
 * Base class for all resource handlers
 * Provides common CRUD operations and utility methods
 */
export abstract class BaseResourceHandler implements IResourceHandler {
  protected context!: IResourceContext;

  /**
   * Get the API endpoint path for this resource
   */
  protected abstract getEndpoint(): string;

  /**
   * Execute an operation for this resource
   */
  public abstract execute(
    operation: string,
    context: IResourceContext,
  ): Promise<IDataObject>;

  /**
   * Get a parameter value from the node
   */
  protected getParameter<T = any>(name: string, defaultValue?: T): T {
    return this.context.executeFunctions.getNodeParameter(
      name,
      this.context.itemIndex,
      defaultValue,
    ) as T;
  }

  /**
   * Make an HTTP request
   */
  protected async request(
    method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE",
    path: string,
    body?: IDataObject,
  ): Promise<IDataObject> {
    const url = `${this.context.credentials.baseUrl}${path}`;

    return makeRequest(
      this.context.executeFunctions,
      this.context.credentials,
      {
        method,
        url,
        body,
      },
    );
  }

  /**
   * Create a new resource
   */
  protected async createResource(body: IDataObject): Promise<IDataObject> {
    return this.request("POST", `/${this.getEndpoint()}/`, body);
  }

  /**
   * Get resource by name
   */
  protected async getByName(
    name: string,
    additionalParams?: Record<string, string>,
  ): Promise<IDataObject> {
    const params = {
      name,
      ...additionalParams,
    };

    const url = buildUrl(
      this.context.credentials.baseUrl,
      `/${this.getEndpoint()}/`,
      params,
    );

    return this.request(
      "GET",
      url.replace(this.context.credentials.baseUrl, ""),
    );
  }

  /**
   * Get resource by reference ID
   */
  protected async getByRefId(
    refId: string,
    additionalParams?: Record<string, string>,
  ): Promise<IDataObject> {
    const params = {
      ref_id: refId,
      ...additionalParams,
    };

    const url = buildUrl(
      this.context.credentials.baseUrl,
      `/${this.getEndpoint()}/`,
      params,
    );

    return this.request(
      "GET",
      url.replace(this.context.credentials.baseUrl, ""),
    );
  }

  /**
   * List resources with optional filters
   */
  protected async listResources(
    folderIdFilter?: string,
    perimeterIdFilter?: string,
    additionalFilters?: Record<string, string>,
  ): Promise<IDataObject> {
    const params = buildFilterParams(
      folderIdFilter,
      perimeterIdFilter,
      additionalFilters,
    );

    const url = buildUrl(
      this.context.credentials.baseUrl,
      `/${this.getEndpoint()}/`,
      params,
    );

    return this.request(
      "GET",
      url.replace(this.context.credentials.baseUrl, ""),
    );
  }

  /**
   * Update a resource
   */
  protected async updateResource(
    id: string,
    body: IDataObject,
  ): Promise<IDataObject> {
    return this.request("PATCH", `/${this.getEndpoint()}/${id}/`, body);
  }

  /**
   * Delete a resource
   */
  protected async deleteResource(id: string): Promise<IDataObject> {
    return this.request("DELETE", `/${this.getEndpoint()}/${id}/`);
  }

  /**
   * Build request body with required and optional fields
   */
  protected buildBody(
    requiredFields: IDataObject,
    optionalFields: IDataObject = {},
  ): IDataObject {
    return buildRequestBody(requiredFields, optionalFields);
  }

  /**
   * Build request body for update operations, filtering out sentinel values
   * Use this for PATCH operations to avoid unintended field resets
   */
  protected buildUpdateBody(fields: IDataObject = {}): IDataObject {
    return buildUpdateBody(fields);
  }

  /**
   * Handle errors consistently
   */
  protected handleError(error: unknown, operation: string): never {
    return handleOperationError(error, this.getEndpoint(), operation);
  }
}
