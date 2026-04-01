import { render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { MetricsSection } from "./metrics-section"

describe("MetricsSection", () => {
  it("renders correctly with required props", () => {
    render(
      <MetricsSection title="Performance Metrics">
        <div>Metric content</div>
      </MetricsSection>
    )

    expect(screen.getByRole("region", { name: "Performance Metrics" })).toBeInTheDocument()
    expect(screen.getByText("Performance Metrics")).toBeInTheDocument()
    expect(screen.getByText("Metric content")).toBeInTheDocument()
  })

  it("shows description when provided", () => {
    render(
      <MetricsSection title="Risk Metrics" description="Risk assessment indicators for the fund">
        <div>Risk content</div>
      </MetricsSection>
    )

    expect(screen.getByText("Risk assessment indicators for the fund")).toBeInTheDocument()
  })

  it("renders as collapsible when isCollapsible is true", () => {
    render(
      <MetricsSection title="Efficiency Metrics" isCollapsible={true}>
        <div>Efficiency content</div>
      </MetricsSection>
    )

    // Should have a button to toggle
    const toggleButton = screen.getByRole("button")
    expect(toggleButton).toBeInTheDocument()
    expect(toggleButton).toHaveAttribute("aria-expanded", "true")
  })

  it("starts collapsed when isCollapsible and isExpanded is false", () => {
    render(
      <MetricsSection title="Consistency Metrics" isCollapsible={true} isExpanded={false}>
        <div>Consistency content</div>
      </MetricsSection>
    )

    const toggleButton = screen.getByRole("button")
    expect(toggleButton).toHaveAttribute("aria-expanded", "false")

    // Content should not be visible
    expect(screen.queryByText("Consistency content")).not.toBeInTheDocument()
  })

  it("calls onToggle when toggle button is clicked", async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()

    render(
      <MetricsSection
        title="Benchmark Comparison"
        isCollapsible={true}
        isExpanded={true}
        onToggle={onToggle}
      >
        <div>Benchmark content</div>
      </MetricsSection>
    )

    const toggleButton = screen.getByRole("button")
    await user.click(toggleButton)

    expect(onToggle).toHaveBeenCalledOnce()
  })

  it("shows chevron icon in correct direction based on expanded state", () => {
    const { rerender } = render(
      <MetricsSection title="Monthly Evolution" isCollapsible={true} isExpanded={true}>
        <div>Monthly content</div>
      </MetricsSection>
    )

    // When expanded, should show ChevronUp (or indicate expanded state)
    const toggleButton = screen.getByRole("button")
    expect(toggleButton).toHaveAttribute("aria-expanded", "true")

    // Re-render as collapsed
    rerender(
      <MetricsSection title="Monthly Evolution" isCollapsible={true} isExpanded={false}>
        <div>Monthly content</div>
      </MetricsSection>
    )

    expect(toggleButton).toHaveAttribute("aria-expanded", "false")
  })

  it("applies custom className", () => {
    render(
      <MetricsSection title="Custom Section" className="custom-metrics-section">
        <div>Custom content</div>
      </MetricsSection>
    )

    const section = screen.getByRole("region")
    expect(section).toHaveClass("custom-metrics-section")
  })

  it("is accessible with proper ARIA attributes", () => {
    render(
      <MetricsSection
        title="Accessible Section"
        description="This section is accessible"
        isCollapsible={true}
        isExpanded={true}
      >
        <div>Accessible content</div>
      </MetricsSection>
    )

    const section = screen.getByRole("region", { name: "Accessible Section" })
    expect(section).toBeInTheDocument()

    const toggleButton = screen.getByRole("button")
    expect(toggleButton).toHaveAccessibleName()
    expect(toggleButton).toHaveAttribute("aria-expanded", "true")
  })

  it("handles keyboard navigation", async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()

    render(
      <MetricsSection title="Keyboard Test" isCollapsible={true} onToggle={onToggle}>
        <div>Keyboard content</div>
      </MetricsSection>
    )

    const toggleButton = screen.getByRole("button")

    // Focus the button
    toggleButton.focus()
    expect(toggleButton).toHaveFocus()

    // Press Enter to toggle
    await user.keyboard("{Enter}")
    expect(onToggle).toHaveBeenCalledOnce()

    // Press Space to toggle
    await user.keyboard(" ")
    expect(onToggle).toHaveBeenCalledTimes(2)
  })

  it("renders without toggle when not collapsible", () => {
    render(
      <MetricsSection title="Fixed Section">
        <div>Fixed content</div>
      </MetricsSection>
    )

    // Should not have a toggle button
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
    // Content should always be visible
    expect(screen.getByText("Fixed content")).toBeInTheDocument()
  })
})
