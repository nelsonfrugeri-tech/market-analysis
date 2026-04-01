import { describe, expect, it } from "vitest"

describe("Test Setup", () => {
  it("should pass basic test", () => {
    expect(true).toBe(true)
  })

  it("should have access to DOM globals", () => {
    expect(typeof document).toBe("object")
    expect(typeof window).toBe("object")
  })
})
