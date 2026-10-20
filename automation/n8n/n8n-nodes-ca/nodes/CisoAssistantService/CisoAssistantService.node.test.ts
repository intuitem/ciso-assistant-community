import { describe, expect, it } from "vitest";
import type {
  IDataObject,
  IExecuteFunctions,
  INodeExecutionData,
  INodePropertyOptions,
} from "n8n-workflow";
import { CisoAssistantService } from "./CisoAssistantService.node";
import { resourceRegistry } from "./registry/ResourceRegistry";

describe("CisoAssistantService description", () => {
  const { properties } = new CisoAssistantService().description;
  const resources = (
    properties.find((p) => p.name === "resource")!
      .options as INodePropertyOptions[]
  ).map((o) => o.value as string);

  it.each(resources)("%s has an operation selector and a handler", (r) => {
    const selectors = properties.filter(
      (p) =>
        p.name === "operation" && p.displayOptions?.show?.resource?.includes(r),
    );
    expect(selectors).toHaveLength(1);
    expect(resourceRegistry.hasHandler(r)).toBe(true);
  });
});

const ID = "6f1c2c4e-8b0a-4d6e-9a51-2f3b7c9d0e11";

describe("output shape by node version", () => {
  const page = { count: 2, next: null, results: [{ id: "a" }, { id: "b" }] };

  async function run(typeVersion: number, operation: string) {
    const urls: string[] = [];
    const params: Record<string, unknown> = {
      resource: "domain",
      operation,
      id: ID,
    };
    const ctx = {
      getInputData: () => [{ json: {} }],
      getNode: () => ({ name: "CA", typeVersion }),
      getCredentials: async () => ({
        baseUrl: "http://ca/api",
        patKey: "t",
        skipTLS: false,
      }),
      getNodeParameter: (n: string, _i: number, d?: unknown) =>
        n in params ? params[n] : d,
      continueOnFail: () => false,
      helpers: {
        httpRequestWithAuthentication: async (
          _t: string,
          o: { url: string },
        ) => {
          urls.push(o.url);
          return operation === "get" ? { id: ID } : page;
        },
        returnJsonArray: (d: IDataObject | IDataObject[]) =>
          (Array.isArray(d) ? d : [d]).map((json) => ({ json })),
        constructExecutionMetaData: (
          items: INodeExecutionData[],
          { itemData }: { itemData: { item: number } },
        ) => items.map((it) => ({ ...it, pairedItem: itemData })),
      },
    } as unknown as IExecuteFunctions;
    const [out] = await new CisoAssistantService().execute.call(ctx);
    return { out, urls };
  }

  it("v1 keeps the {count, results} envelope", async () => {
    const { out } = await run(1, "list");
    expect(out).toEqual([
      { json: { count: 2, results: page.results }, pairedItem: { item: 0 } },
    ]);
  });

  it("v2 emits one item per row", async () => {
    const { out } = await run(2, "list");
    expect(out.map((o) => o.json)).toEqual(page.results);
    expect(out.every((o) => o.pairedItem?.item === 0)).toBe(true);
  });

  it("get fetches one object by ID", async () => {
    const { out, urls } = await run(2, "get");
    expect(urls).toEqual([`http://ca/api/folders/${ID}/`]);
    expect(out.map((o) => o.json)).toEqual([{ id: ID }]);
  });
});
