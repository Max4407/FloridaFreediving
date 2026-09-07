import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SignupPage } from "./SignupPage";

describe("SignupPage", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/signup?dive=abc123");
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ public_id: "abc123", title: "Blue Heron", description: "Morning dive", location: "Riviera Beach", starts_at: "2026-09-12T12:00:00Z", capacity: 10, remaining: 2, next_status: "confirmed" }),
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("only asks renters for gear sizes", async () => {
    render(<SignupPage />);
    expect(await screen.findByText("Blue Heron")).toBeInTheDocument();
    expect(screen.queryByLabelText("Wetsuit size")).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/I need rental gear/));
    expect(screen.getByLabelText("Wetsuit size")).toBeRequired();
    expect(screen.getByLabelText("US unisex shoe size")).toBeRequired();
  });

  it("requires a pickup location for carpools", async () => {
    render(<SignupPage />);
    await screen.findByText("Blue Heron");
    fireEvent.click(screen.getByLabelText(/I need a carpool/));
    await waitFor(() => expect(screen.getByLabelText("Pickup location")).toBeRequired());
  });
});
