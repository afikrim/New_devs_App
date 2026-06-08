import { describe, it, expect } from "vitest";
import { formatMoney } from "./money";

describe("formatMoney", () => {
  it("formats trailing-zero decimals to 2 places", () => {
    expect(formatMoney("2250.000")).toBe("2,250.00");
    expect(formatMoney("1000.00")).toBe("1,000.00");
    expect(formatMoney("4975.50")).toBe("4,975.50");
  });

  it("rounds the third decimal half-up", () => {
    expect(formatMoney("333.334")).toBe("333.33");
    expect(formatMoney("333.335")).toBe("333.34");
  });

  it("carries rounding into the integer part", () => {
    expect(formatMoney("9.999")).toBe("10.00");
    expect(formatMoney("99.999")).toBe("100.00");
    expect(formatMoney("999.999")).toBe("1,000.00");
  });

  it("groups thousands", () => {
    expect(formatMoney("1234567.5")).toBe("1,234,567.50");
    expect(formatMoney("1000000")).toBe("1,000,000.00");
  });

  it("handles zero, empty, and missing values", () => {
    expect(formatMoney("0")).toBe("0.00");
    expect(formatMoney("")).toBe("0.00");
    // @ts-expect-error exercising a null/undefined runtime value
    expect(formatMoney(undefined)).toBe("0.00");
  });

  it("handles negatives", () => {
    expect(formatMoney("-5.005")).toBe("-5.01");
    expect(formatMoney("-1234.5")).toBe("-1,234.50");
  });

  it("does not lose precision the way a float would", () => {
    // 0.1 + 0.2 in float is 0.30000000000000004; the string is exact.
    expect(formatMoney("0.30")).toBe("0.30");
    // A long decimal string stays exact through formatting.
    expect(formatMoney("9999999.994")).toBe("9,999,999.99");
  });
});
