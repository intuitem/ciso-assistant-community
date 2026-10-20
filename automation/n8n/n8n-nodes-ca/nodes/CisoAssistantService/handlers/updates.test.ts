import { describe, expect, it } from "vitest";
import type {
  IDataObject,
  IExecuteFunctions,
  IHttpRequestOptions,
  INodeExecutionData,
  INodeProperties,
} from "n8n-workflow";
import { CisoAssistantService } from "../CisoAssistantService.node";

const { properties } = new CisoAssistantService().description;

// Mirrors n8n: an untouched parameter resolves to the default of the variant shown for this version.
function defaultFor(name: string, version: number, params: IDataObject) {
  const shown = (p: INodeProperties) =>
    Object.entries(p.displayOptions?.show ?? {}).every(([key, allowed]) =>
      key === "@version"
        ? (allowed as Array<number | { _cnd: { gte: number } }>).some((a) =>
            typeof a === "number" ? a === version : version >= a._cnd.gte,
          )
        : (allowed as unknown[]).includes(params[key]),
    );
  return properties.find((p) => p.name === name && shown(p))?.default;
}

async function run(
  typeVersion: number,
  params: IDataObject,
  respond: (o: IHttpRequestOptions) => IDataObject,
) {
  const calls: IHttpRequestOptions[] = [];
  const ctx = {
    getInputData: () => [{ json: {} }],
    getNode: () => ({ name: "CA", typeVersion }),
    getCredentials: async () => ({
      baseUrl: "http://ca/api",
      patKey: "t",
      skipTLS: false,
    }),
    getNodeParameter: (n: string, _i: number, fallback?: unknown) =>
      n in params
        ? params[n]
        : (defaultFor(n, typeVersion, params) ?? fallback),
    continueOnFail: () => false,
    helpers: {
      httpRequestWithAuthentication: async (
        _t: string,
        o: IHttpRequestOptions,
      ) => {
        calls.push(o);
        return respond(o);
      },
      returnJsonArray: (d: IDataObject | IDataObject[]) =>
        (Array.isArray(d) ? d : [d]).map((json) => ({ json })),
      constructExecutionMetaData: (items: INodeExecutionData[]) => items,
    },
  } as unknown as IExecuteFunctions;
  await new CisoAssistantService().execute.call(ctx);
  return calls;
}

const updateObservation = {
  resource: "audit",
  operation: "updateRequirementAssessment",
  complianceAssessmentId: "ca-1",
  requirementRefId: "A.5.2",
  requirementAssessmentObservation: "checked",
};
const oneMatch = (o: IHttpRequestOptions) =>
  o.method === "GET" ? { count: 1, results: [{ id: "ra-2" }] } : {};

describe("update requirement assessment", () => {
  it("v2 sends only the fields that were set", async () => {
    const calls = await run(2, updateObservation, oneMatch);
    expect(calls[0].url).toContain("requirement__ref_id=A.5.2");
    expect(calls[1]).toMatchObject({
      method: "PATCH",
      url: "http://ca/api/requirement-assessments/ra-2/",
      body: { observation: "checked" },
    });
  });

  it("v1 keeps its saved behaviour", async () => {
    const calls = await run(1, updateObservation, oneMatch);
    expect(calls[1].body).toEqual({
      status: "to_do",
      result: "not_assessed",
      observation: "checked",
      score: 0,
    });
  });

  it("refuses to update when the lookup is ambiguous", async () => {
    const calls: IHttpRequestOptions[] = [];
    await expect(
      run(2, updateObservation, (o) => {
        calls.push(o);
        return { count: 2, results: [{ id: "a" }, { id: "b" }] };
      }),
    ).rejects.toThrow(/expected exactly one/);
    expect(calls.map((c) => c.method)).toEqual(["GET"]);
  });
});

describe("create incident", () => {
  it("leaves untouched status, severity and detection to the model defaults", async () => {
    const calls = await run(
      2,
      {
        resource: "incident",
        operation: "create",
        incidentName: "Phishing",
        folderId: "f-1",
      },
      () => ({ id: "i-1" }),
    );
    expect(calls[0].body).toEqual({
      name: "Phishing",
      folder: "f-1",
      description: "",
    });
  });
});

describe("object IDs", () => {
  const uuid = "6f1c2c4e-8b0a-4d6e-9a51-2f3b7c9d0e11";
  it.each(["..", ".", `../folders/${uuid}`, `${uuid}?x=1`, ""])(
    "rejects %j before any request is sent",
    async (bad) => {
      for (const params of [
        { resource: "asset", operation: "get", id: bad },
        {
          resource: "asset",
          operation: "update",
          assetId: bad,
          assetNameUpdate: "x",
        },
      ]) {
        const calls: IHttpRequestOptions[] = [];
        await expect(
          run(2, params, (o) => {
            calls.push(o);
            return {};
          }),
        ).rejects.toThrow(/expected a UUID/);
        expect(calls).toEqual([]);
      }
    },
  );

  it("accepts a UUID with surrounding whitespace", async () => {
    const calls = await run(
      2,
      { resource: "asset", operation: "get", id: ` ${uuid} ` },
      () => ({}),
    );
    expect(calls[0].url).toBe(`http://ca/api/assets/${uuid}/`);
  });
});
