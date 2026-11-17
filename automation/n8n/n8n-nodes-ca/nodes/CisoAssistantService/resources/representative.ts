import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["representative"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new representative for an entity",
      action: "Create representative",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a representative by ID",
      action: "Get a representative",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all representatives",
      action: "Get many representatives",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Entity UUID",
    name: "representativeEntityId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["representative"],
        operation: ["create", "list"],
      },
    },
    default: "",
    placeholder: "entity-uuid-here",
    description: "UUID of the entity",
    required: true,
  },
  {
    displayName: "Email",
    name: "representativeEmail",
    type: "string",
    displayOptions: {
      show: {
        resource: ["representative"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "contact@example.com",
    description: "Email address of the representative (unique)",
    required: true,
  },
  {
    displayName: "First Name",
    name: "representativeFirstName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["representative"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "John",
    description: "First name of the representative",
  },
  {
    displayName: "Last Name",
    name: "representativeLastName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["representative"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Doe",
    description: "Last name of the representative",
  },
  {
    displayName: "Phone",
    name: "representativePhone",
    type: "string",
    displayOptions: {
      show: {
        resource: ["representative"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "+1234567890",
    description: "Phone number of the representative",
  },
  {
    displayName: "Role",
    name: "representativeRole",
    type: "string",
    displayOptions: {
      show: {
        resource: ["representative"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Account Manager",
    description: "Role or position of the representative",
  },
  {
    displayName: "Description",
    name: "representativeDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["representative"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Additional details about the representative",
    description: "Representative description",
  },
];
