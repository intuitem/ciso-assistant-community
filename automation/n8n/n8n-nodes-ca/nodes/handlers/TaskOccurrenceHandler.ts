import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for task occurrence operations
 */
export class TaskOccurrenceHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "task-occurrences";
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
    const folderId = this.getParameter<string>("folderId");
    const taskDueDate = this.getParameter<string>("taskDueDate", "");
    const taskStatus = this.getParameter<string>("taskStatus", "pending");
    const taskObservation = this.getParameter<string>("taskObservation", "");

    const body = this.buildBody(
      {
        folder: folderId,
        status: taskStatus,
      },
      {
        due_date: taskDueDate,
        observation: taskObservation,
      },
    );

    return this.createResource(body);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const taskId = this.getParameter<string>("taskId");
    const taskDueDate = this.getParameter<string>("taskDueDate", "");
    const taskStatus = this.getParameter<string>("taskStatus", "");
    const taskObservation = this.getParameter<string>("taskObservation", "");

    const body = this.buildBody(
      {},
      {
        due_date: taskDueDate,
        status: taskStatus,
        observation: taskObservation,
      },
    );

    return this.updateResource(taskId, body);
  }
}
