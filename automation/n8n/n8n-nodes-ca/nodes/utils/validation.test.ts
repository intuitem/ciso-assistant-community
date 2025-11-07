import { buildUpdateBody } from "./validation";

describe("buildUpdateBody", () => {
  it("should filter out empty string sentinels", () => {
    const result = buildUpdateBody({
      description: "",
      name: "Test Name",
      status: "",
    });

    expect(result).toEqual({ name: "Test Name" });
  });

  it("should filter out -- placeholder sentinels", () => {
    const result = buildUpdateBody({
      status: "--",
      name: "Test Name",
      ref_id: "REF-123",
    });

    expect(result).toEqual({ name: "Test Name", ref_id: "REF-123" });
  });

  it("should filter out -1 numeric sentinels", () => {
    const result = buildUpdateBody({
      severity: -1,
      score: 5,
      impact: -1,
    });

    expect(result).toEqual({ score: 5 });
  });

  it("should filter out null and undefined", () => {
    const result = buildUpdateBody({
      field1: null,
      field2: undefined,
      field3: "value",
    });

    expect(result).toEqual({ field3: "value" });
  });

  it("should include valid 0 values", () => {
    const result = buildUpdateBody({
      severity: 0,
      count: 0,
    });

    expect(result).toEqual({ severity: 0, count: 0 });
  });

  it("should include boolean values", () => {
    const result = buildUpdateBody({
      enabled: true,
      archived: false,
    });

    expect(result).toEqual({ enabled: true, archived: false });
  });

  it("should handle VulnerabilityHandler update with undefined fields", () => {
    // Simulates user not setting any optional fields (getParameter returns undefined)
    const result = buildUpdateBody({
      description: undefined,
      status: undefined,
      severity: undefined,
      ref_id: undefined,
    });

    // Should result in empty body - no unintended field resets!
    expect(result).toEqual({});
  });

  it("should handle VulnerabilityHandler update with sentinel values", () => {
    // Simulates old behavior where defaults were provided
    const result = buildUpdateBody({
      description: "",
      status: "--",
      severity: -1,
      ref_id: "",
    });

    // Should still filter these out
    expect(result).toEqual({});
  });

  it("should handle RiskScenarioHandler update with partial fields", () => {
    // User only wants to update treatment, not reset other fields
    const result = buildUpdateBody({
      description: "",
      treatment: "accept",
      inherent_proba: -1,
      inherent_impact: -1,
      current_proba: 3,
      current_impact: -1,
    });

    // Only sends the fields that were actually set
    expect(result).toEqual({
      treatment: "accept",
      current_proba: 3,
    });
  });

  it("should handle arrays and objects", () => {
    const result = buildUpdateBody({
      tags: ["tag1", "tag2"],
      metadata: { key: "value" },
      empty_field: "",
    });

    expect(result).toEqual({
      tags: ["tag1", "tag2"],
      metadata: { key: "value" },
    });
  });
});
