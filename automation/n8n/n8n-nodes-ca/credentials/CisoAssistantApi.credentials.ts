import type {
  IAuthenticateGeneric,
  Icon,
  ICredentialTestRequest,
  ICredentialType,
  INodeProperties,
} from "n8n-workflow";

export class CisoAssistantApi implements ICredentialType {
  name = "cisoAssistantApi";
  displayName = "CISO Assistant API";
  icon: Icon = "file:../icons/cisoAssistant.svg";
  documentationUrl =
    "https://github.com/intuitem/ciso-assistant-community/tree/main/automation/n8n/n8n-nodes-ca#credentials";
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
      description:
        "Personal Access Token created from your CISO Assistant user profile",
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
      displayName: "Skip TLS Verification",
      name: "skipTLS",
      type: "boolean",
      default: false,
      description:
        "Whether to accept self-signed or invalid TLS certificates. Only enable on a trusted network.",
    },
  ];

  authenticate: IAuthenticateGeneric = {
    type: "generic",
    properties: {
      headers: {
        Authorization: "=Token {{$credentials.patKey}}",
      },
    },
  };

  test: ICredentialTestRequest = {
    request: {
      baseURL: "={{$credentials.baseUrl}}",
      url: "/build/",
      skipSslCertificateValidation: "={{$credentials.skipTLS}}",
    },
  };
}
