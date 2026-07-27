import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReliabilityBadge } from "./ReliabilityBadge";

describe("ReliabilityBadge", () => {
  it("mostra fascia e punteggio arrotondato", () => {
    render(<ReliabilityBadge band="high" score={82.46} />);

    expect(screen.getByText(/Alta/)).toHaveTextContent("Alta · 82");
  });
});
