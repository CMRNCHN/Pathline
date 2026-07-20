import { afterEach, describe, expect, it, vi } from "vitest";

describe("apiUrl", () => {
  afterEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it("prefers the desktop-injected absolute origin over Vite /api", async () => {
    vi.stubGlobal("window", {
      __pathlineApiBase: "http://127.0.0.1:8000/",
      __TAURI_INTERNALS__: {},
    });
    const { apiUrl } = await import("./api");
    expect(apiUrl()).toBe("http://127.0.0.1:8000");
  });

  it("never uses the Vite /api proxy path inside Tauri", async () => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });
    const { apiUrl } = await import("./api");
    expect(apiUrl()).toBe("http://127.0.0.1:8000");
    expect(apiUrl().includes("/api")).toBe(false);
  });
});
