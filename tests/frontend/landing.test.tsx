import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LandingPage } from "../../frontend/src/pages/LandingPage";

describe("public landing page", () => {
  it("explains Mwangaza with exactly three capabilities and configured links", () => {
    render(<LandingPage links={{ dashboard: "/overview", github: "https://github.com/example/project", demo: "/overview?demo=1" }} />);
    expect(screen.getByRole("heading", { name: /Mwangaza Bringing Light to Early Action/ })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(3);
    expect(screen.getAllByRole("link", { name: "Open dashboard" })[0]).toHaveAttribute("href", "/overview");
    expect(screen.getByRole("link", { name: "View on GitHub" })).toHaveAttribute("href", "https://github.com/example/project");
  });
  it("omits invalid optional CTAs without breaking the dashboard action", () => {
    render(<LandingPage links={{ dashboard: "/overview", github: "javascript:alert(1)", demo: "" }} />);
    expect(screen.queryByRole("link", { name: "View on GitHub" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Explore the demo" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open dashboard" })).toHaveLength(2);
  });
  it("uses qualitative claims and a responsive overflow-safe root", () => {
    const { container } = render(<LandingPage />);
    expect(container.querySelector(".landing-page")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\b\d+(?:\.\d+)?%\b/);
  });
});
