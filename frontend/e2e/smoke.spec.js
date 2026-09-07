import { expect, test } from "@playwright/test";

test("officer can sign in and create a dive", async ({ page }) => {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const browserTestDate = `${now.getFullYear()}-${month}-15T08:30`;
  await page.goto("/dash");
  await expect(page.getByRole("heading", { name: "Officer access" })).toBeVisible();
  await page.getByLabel("Password").fill("club-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "+ New dive" })).toBeVisible();

  await page.getByRole("button", { name: "+ New dive" }).click();
  await page.getByLabel("Title").fill("Browser Test Dive");
  await page.getByLabel("Description").fill("Created by the browser smoke test.");
  await page.getByLabel("Location").fill("Phil Foster Park");
  await page.getByLabel("Date and time (Eastern)").fill(browserTestDate);
  await page.getByLabel("Capacity").fill("8");
  await page.getByRole("button", { name: "Save dive" }).click();

  await expect(page.getByRole("button", { name: /Browser Test Dive/ })).toBeVisible();
});
