import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../api";
import { Dashboard, InventoryPanel } from "./Dashboard";

vi.mock("../../api", () => ({
  api: vi.fn(),
  easternDateTime: vi.fn(),
}));

describe("InventoryPanel", () => {
  beforeEach(() => api.mockReset());

  it("hides depleted equipment and removes an item when its count reaches zero", async () => {
    api.mockResolvedValue(null);
    const reload = vi.fn();
    render(<InventoryPanel inventory={[
      { id: "empty", category: "mask", quantity: 0 },
      { id: "last", category: "weight_set", quantity: 1 },
    ]} reload={reload} />);

    expect(screen.queryByText("Masks")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Decrease Weight sets" }));

    await waitFor(() => expect(api).toHaveBeenCalledWith(
      "/api/officer/inventory/last",
      { method: "DELETE" },
    ));
    expect(reload).toHaveBeenCalled();
  });
});

describe("Dashboard photography", () => {
  beforeEach(() => {
    api.mockReset();
    api.mockImplementation((path) => {
      if (path === "/api/officer/dives") return Promise.resolve([]);
      if (path === "/api/officer/officers") return Promise.resolve([]);
      if (path === "/api/officer/inventory") return Promise.resolve([]);
      return Promise.resolve(null);
    });
  });

  it("selects the background class that belongs to each officer tab", async () => {
    const { container } = render(<Dashboard onLogout={vi.fn()} />);
    await waitFor(() => expect(api).toHaveBeenCalledTimes(3));
    const shell = container.firstChild;

    expect(shell).toHaveClass("dashboard-calendar");
    fireEvent.click(screen.getByRole("button", { name: "Officers" }));
    expect(shell).toHaveClass("dashboard-officers");
    fireEvent.click(screen.getByRole("button", { name: "Gear" }));
    expect(shell).toHaveClass("dashboard-inventory");
  });
});

describe("Dashboard ride details", () => {
  beforeEach(() => {
    api.mockReset();
    const startsAt = new Date().toISOString();
    api.mockImplementation((path) => {
      if (path === "/api/officer/dives") return Promise.resolve([{
        id: "dive-1", public_id: "abc123", title: "Blue Heron", description: "", location: "Riviera Beach", starts_at: startsAt,
        capacity: 10, confirmed_count: 2, waitlist_count: 0, rides_needed: 1, seats_available: 3,
        officers: [], assigned_officer_ids: [], warnings: [], gear: [], waitlisted: [],
        confirmed: [{
          id: "signup-1", name: "Dana Driver", email: "dana@example.com", phone: "561-555-0199", status: "confirmed",
          needs_carpool: false, pickup_location: null, can_drive: true, available_seats: 3,
          needs_gear: false, suit_size: null, shoe_size: null,
        }],
      }]);
      if (path === "/api/officer/officers") return Promise.resolve([]);
      if (path === "/api/officer/inventory") return Promise.resolve([]);
      return Promise.resolve(null);
    });
  });

  it("shows confirmed ride totals and each diver's contact and driving details", async () => {
    render(<Dashboard onLogout={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /Blue Heron/ }));

    expect(screen.getByText("Rides needed").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("Seats offered").nextSibling).toHaveTextContent("3");
    expect(screen.getByText("561-555-0199")).toBeInTheDocument();
    expect(screen.getByText("Driver · 3 seats")).toBeInTheDocument();
  });
});
