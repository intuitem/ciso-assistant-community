import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["evidence"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new evidence",
      action: "Create evidence",
    },
    {
      name: "Get",
      value: "get",
      description: "Get an evidence by ID",
      action: "Get an evidence",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get an evidence by its name (case-sensitive)",
      action: "Get evidence by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all evidences",
      action: "Get many evidences",
    },
    {
      name: "List Revisions",
      value: "listRevisions",
      description: "List all revisions of an evidence",
      action: "List evidence revisions",
    },
    {
      name: "Submit Revision",
      value: "submitRevision",
      description: "Submit a new revision of the evidence (link or attachment)",
      action: "Submit evidence revision",
    },
    {
      name: "Update Envelope",
      value: "update",
      description:
        "Update evidence envelope data (name, description, status, etc.)",
      action: "Update evidence envelope",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Evidence Name",
    name: "evidenceName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Compliance Report 2025",
    description: "Name of the evidence (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain)",
    required: true,
  },
  {
    displayName: "Description",
    name: "evidenceDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the evidence",
    description: "Evidence description",
  },
  {
    displayName: "Status",
    name: "evidenceStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["create"],
      },
    },
    options: [
      {
        name: "Approved",
        value: "approved",
      },
      {
        name: "Draft",
        value: "draft",
      },
      {
        name: "Expired",
        value: "expired",
      },
      {
        name: "In Review",
        value: "in_review",
      },
      {
        name: "Missing",
        value: "missing",
      },
      {
        name: "Rejected",
        value: "rejected",
      },
    ],
    default: "draft",
    description: "Status of the evidence",
  },
  {
    displayName: "Expiry Date",
    name: "evidenceExpiryDate",
    type: "string",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "2025-12-31",
    description: "Expiry date (YYYY-MM-DD format)",
  },
  {
    displayName: "Evidence UUID",
    name: "evidenceId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "evidence-uuid-here",
    description: "The UUID of the evidence to update",
    required: true,
  },
  {
    displayName: "Status",
    name: "evidenceStatusUpdate",
    type: "options",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["update"],
      },
    },
    options: [
      {
        name: "Approved",
        value: "approved",
      },
      {
        name: "Draft",
        value: "draft",
      },
      {
        name: "Expired",
        value: "expired",
      },
      {
        name: "In Review",
        value: "in_review",
      },
      {
        name: "Missing",
        value: "missing",
      },
      {
        name: "Rejected",
        value: "rejected",
      },
    ],
    default: "draft",
    description: "Status of the evidence",
  },
  {
    displayName: "Evidence UUID",
    name: "evidenceIdForRevision",
    type: "string",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["submitRevision", "listRevisions"],
      },
    },
    default: "",
    placeholder: "evidence-uuid-here",
    description: "The UUID of the evidence",
    required: true,
  },
  {
    displayName: "Revision Type",
    name: "evidenceRevisionType",
    type: "options",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["submitRevision"],
      },
    },
    options: [
      {
        name: "File Upload",
        value: "file",
      },
      {
        name: "Link",
        value: "link",
      },
    ],
    default: "link",
    description: "Whether to submit a link or upload a file attachment",
  },
  {
    displayName: "Link",
    name: "evidenceRevisionLink",
    type: "string",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["submitRevision"],
        evidenceRevisionType: ["link"],
      },
    },
    default: "",
    placeholder: "https://example.com/document.pdf",
    description: "URL link to the evidence",
  },
  {
    displayName: "Binary Property",
    name: "binaryPropertyName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["submitRevision"],
        evidenceRevisionType: ["file"],
      },
    },
    default: "data",
    placeholder: "data",
    description: "Name of the binary property containing the file to upload",
    required: true,
  },
  {
    displayName: "Observation",
    name: "evidenceRevisionObservation",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["evidence"],
        operation: ["submitRevision"],
      },
    },
    default: "",
    placeholder: "Revision notes or observations",
    description: "Observation notes for this revision",
  },
];
