import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../api";
import { InventoryPanel } from "./Dashboard";

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
