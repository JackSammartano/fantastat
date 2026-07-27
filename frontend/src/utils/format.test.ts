import { describe, expect, it } from "vitest";
import { formatNumber, formatPercent } from "./format";

describe("formattazione", () => {
  it("distingue valori mancanti da zero", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(0)).toBe("0,00");
  });

  it("formatta una proporzione come percentuale", () => {
    expect(formatPercent(0.75)).toBe("75%");
  });
});
