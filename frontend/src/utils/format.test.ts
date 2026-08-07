import { describe, expect, it } from "vitest";
import { formatNumber, formatPercent, trendDirection } from "./format";

describe("formattazione", () => {
  it("distingue valori mancanti da zero", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(0)).toBe("0,00");
  });

  it("formatta una proporzione come percentuale", () => {
    expect(formatPercent(0.75)).toBe("75%");
  });

  it("considera stabile un trend che a video diventa zero", () => {
    expect(trendDirection(0.0048738648)).toBe(0);
    expect(trendDirection(0.006)).toBe(1);
    expect(trendDirection(-0.006)).toBe(-1);
  });
});
