import { describe, expect, it } from "vitest";
import { calculateMatchdayTrend } from "./matchdayTrend";

describe("calculateMatchdayTrend", () => {
  it("calcola forma e crescita sugli ultimi cinque voti", () => {
    const result = calculateMatchdayTrend([5, 5.5, 6, 6.5, 7].map((vote, index) => ({ matchday: index + 1, vote })));
    expect(result.formAverage).toBe(6);
    expect(result.slope).toBeCloseTo(0.5);
    expect(result.direction).toBe(1);
    expect(result.sampleSize).toBe(5);
  });

  it("ignora i senza voto e richiede almeno tre voti per la pendenza", () => {
    const result = calculateMatchdayTrend([{ matchday: 1, vote: 6 }, { matchday: 2, vote: null }, { matchday: 3, vote: 6.1 }]);
    expect(result.formAverage).toBeCloseTo(6.05);
    expect(result.slope).toBeNull();
    expect(result.direction).toBeNull();
  });

  it("classifica come stabile una variazione inferiore alla soglia", () => {
    const result = calculateMatchdayTrend([6, 6.05, 6.08, 6.1, 6.12].map((vote, index) => ({ matchday: index + 1, vote })));
    expect(result.direction).toBe(0);
  });
});
