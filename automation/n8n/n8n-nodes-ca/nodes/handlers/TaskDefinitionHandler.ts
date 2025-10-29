import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for task definition operations
 */
export class TaskDefinitionHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "task-definitions";
  }

  public async execute(
    operation: string,
    context: IResourceContext,
  ): Promise<IDataObject> {
    this.context = context;

    try {
      switch (operation) {
        case "create":
          return await this.create();
        case "getByName":
          return await this.getByNameOp();
        case "list":
          return await this.list();
        case "update":
          return await this.update();
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async create(): Promise<IDataObject> {
    const taskDefinitionName = this.getParameter<string>("taskDefinitionName");
    const folderId = this.getParameter<string>("folderId");
    const taskDefinitionDescription = this.getParameter<string>(
      "taskDefinitionDescription",
      "",
    );
    const taskDefinitionTaskDate = this.getParameter<string>(
      "taskDefinitionTaskDate",
      "",
    );
    const taskDefinitionIsRecurrent = this.getParameter<boolean>(
      "taskDefinitionIsRecurrent",
      false,
    );
    const taskDefinitionEnabled = this.getParameter<boolean>(
      "taskDefinitionEnabled",
      true,
    );

    const body = this.buildBody(
      {
        name: taskDefinitionName,
        folder: folderId,
        is_recurrent: taskDefinitionIsRecurrent,
        enabled: taskDefinitionEnabled,
      },
      {
        description: taskDefinitionDescription,
        task_date: taskDefinitionTaskDate,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const taskDefinitionName = this.getParameter<string>("taskDefinitionName");
    const folderId = this.getParameter<string>("folderId");

    return this.getByName(taskDefinitionName, { folder: folderId });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const taskDefinitionId = this.getParameter<string>("taskDefinitionId");
    const taskDefinitionTaskDateUpdate = this.getParameter<string>(
      "taskDefinitionTaskDateUpdate",
      "",
    );
    const taskDefinitionEnabledUpdate = this.getParameter<boolean>(
      "taskDefinitionEnabledUpdate",
      true,
    );

    const body = this.buildUpdateBody({
      task_date: taskDefinitionTaskDateUpdate,
      enabled: taskDefinitionEnabledUpdate,
    });

    return this.updateResource(taskDefinitionId, body);
  }
}
