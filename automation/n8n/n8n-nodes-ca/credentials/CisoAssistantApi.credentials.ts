import { ICredentialType, INodeProperties } from "n8n-workflow";

export class CisoAssistantApi implements ICredentialType {
  name = "cisoAssistantApi";
  displayName = "CISO Assistant API";
  documentationUrl = "https://ca-api-doc.pages.dev";
  properties: INodeProperties[] = [
    {
      displayName: "Personal Access Token (PAT)",
      name: "patKey",
      type: "string",
      typeOptions: {
        password: true,
      },
      default: "",
      required: true,
      description: "The PAT key to authenticate",
    },
    {
      displayName: "API URL",
      name: "baseUrl",
      type: "string",
      default: "http://localhost:8000/api",
      required: true,
      description: "The base URL for CISO Assistant API",
    },
    {
      displayName: "Skip TLS verification",
      name: "skipTLS",
      type: "boolean",
      default: "true",
      required: true,
      description: "Enable TLS checking if there is a valid certificate",
    },
  ];
}
