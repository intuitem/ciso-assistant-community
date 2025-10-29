import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";
import { buildUrl } from "../utils/http";

/**
 * Handler for evidence operations
 */
export class EvidenceHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "evidences";
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
        case "submitRevision":
          return await this.submitRevision();
        case "listRevisions":
          return await this.listRevisions();
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async create(): Promise<IDataObject> {
    const evidenceName = this.getParameter<string>("evidenceName");
    const folderId = this.getParameter<string>("folderId");
    const evidenceDescription = this.getParameter<string>(
      "evidenceDescription",
      "",
    );
    const evidenceStatus = this.getParameter<string>("evidenceStatus", "draft");
    const evidenceExpiryDate = this.getParameter<string>(
      "evidenceExpiryDate",
      "",
    );

    const body = this.buildBody(
      {
        name: evidenceName,
        folder: folderId,
        status: evidenceStatus,
      },
      {
        description: evidenceDescription,
        expiry_date: evidenceExpiryDate,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const evidenceName = this.getParameter<string>("evidenceName");
    const folderId = this.getParameter<string>("folderId");

    return this.getByName(evidenceName, { folder: folderId });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const evidenceId = this.getParameter<string>("evidenceId");
    const evidenceStatusUpdate = this.getParameter<string>(
      "evidenceStatusUpdate",
      "",
    );

    const body = this.buildUpdateBody({ status: evidenceStatusUpdate });

    return this.updateResource(evidenceId, body);
  }

  private async submitRevision(): Promise<IDataObject> {
    const evidenceIdForRevision = this.getParameter<string>(
      "evidenceIdForRevision",
    );
    const evidenceRevisionType = this.getParameter<string>(
      "evidenceRevisionType",
    );
    const evidenceRevisionObservation = this.getParameter<string>(
      "evidenceRevisionObservation",
      "",
    );

    if (evidenceRevisionType === "file") {
      return await this.submitFileRevision(
        evidenceIdForRevision,
        evidenceRevisionObservation,
      );
    } else {
      return await this.submitLinkRevision(
        evidenceIdForRevision,
        evidenceRevisionObservation,
      );
    }
  }

  private async submitFileRevision(
    evidenceId: string,
    observation: string,
  ): Promise<IDataObject> {
    const binaryPropertyName = this.getParameter<string>("binaryPropertyName");
    const binaryData = this.context.executeFunctions.helpers.assertBinaryData(
      this.context.itemIndex,
      binaryPropertyName,
    );
    const dataBuffer =
      await this.context.executeFunctions.helpers.getBinaryDataBuffer(
        this.context.itemIndex,
        binaryPropertyName,
      );

    const filename = binaryData.fileName || "evidence-file";

    // Step 1: Create a new evidence revision
    const revisionData: any = {
      evidence: evidenceId,
    };
    if (observation) {
      revisionData.observation = observation;
    }

    const revisionResponse: any = await this.request(
      "POST",
      "/evidence-revisions/",
      revisionData,
    );
    const newRevisionId = revisionResponse.id;

    // Step 2: Upload the file to the new revision
    await this.context.executeFunctions.helpers.httpRequest({
      method: "POST",
      url: `${this.context.credentials.baseUrl}/evidence-revisions/${newRevisionId}/upload/`,
      headers: {
        Authorization: `Token ${this.context.credentials.patKey}`,
        "Content-Disposition": `attachment; filename=${encodeURIComponent(filename)}`,
      },
      body: dataBuffer,
      json: false,
      skipSslCertificateValidation: this.context.credentials.skipTLS,
    });

    return revisionResponse;
  }

  private async submitLinkRevision(
    evidenceId: string,
    observation: string,
  ): Promise<IDataObject> {
    const evidenceRevisionLink = this.getParameter<string>(
      "evidenceRevisionLink",
      "",
    );

    const revisionData: any = {
      evidence: evidenceId,
    };
    if (observation) {
      revisionData.observation = observation;
    }
    if (evidenceRevisionLink) {
      revisionData.link = evidenceRevisionLink;
    }

    return this.request("POST", "/evidence-revisions/", revisionData);
  }

  private async listRevisions(): Promise<IDataObject> {
    const evidenceIdForRevision = this.getParameter<string>(
      "evidenceIdForRevision",
    );

    const url = buildUrl(
      this.context.credentials.baseUrl,
      "/evidence-revisions/",
      {
        evidence: evidenceIdForRevision,
      },
    );

    return this.request(
      "GET",
      url.replace(this.context.credentials.baseUrl, ""),
    );
  }
}
