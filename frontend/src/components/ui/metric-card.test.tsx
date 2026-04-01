import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { MetricCard } from "./metric-card"

describe("MetricCard", () => {
  it("renders correctly with required props", () => {
    render(<MetricCard title="Total Return" value={8.45} />)

    expect(screen.getByRole("heading", { name: "Total Return" })).toBeInTheDocument()
    expect(screen.getByText("8,45")).toBeInTheDocument()
  })

  it("formats percentage values correctly", () => {
    render(<MetricCard title="Annual Return" value={12.34} format="percentage" />)

    expect(screen.getByText("12,34%")).toBeInTheDocument()
  })

  it("formats currency values correctly", () => {
    render(<MetricCard title="NAV" value={1234.56} format="currency" />)

    expect(screen.getByText("R$ 1.234,56")).toBeInTheDocument()
  })

  it("shows trend indicator when provided", () => {
    render(
      <MetricCard
        title="Monthly Return"
        value={2.15}
        trend="up"
        trendValue={0.25}
        format="percentage"
      />
    )

    // Should show the trend value
    expect(screen.getByText("+0,25%")).toBeInTheDocument()
    // Should have appropriate CSS class for trend direction
    const trendElement = screen.getByText("+0,25%").closest("div")
    expect(trendElement).toHaveClass("text-green-600")
  })

  it("shows loading state", () => {
    render(<MetricCard title="Loading Metric" value={0} isLoading={true} />)

    expect(screen.getByTestId("metric-card-skeleton")).toBeInTheDocument()
  })

  it("displays tooltip when provided", () => {
    render(
      <MetricCard title="Sharpe Ratio" value={1.34} tooltip="Risk-adjusted return measurement" />
    )

    // Should render tooltip trigger (help icon)
    const helpIcon = screen.getByTestId("help-icon")
    expect(helpIcon).toBeInTheDocument()
  })

  it("applies custom precision for number formatting", () => {
    render(<MetricCard title="Beta" value={1.2345} format="number" precision={3} />)

    expect(screen.getByText("1,235")).toBeInTheDocument()
  })

  it("handles negative trend values correctly", () => {
    render(
      <MetricCard
        title="Drawdown"
        value={-5.67}
        trend="down"
        trendValue={-1.23}
        format="percentage"
      />
    )

    expect(screen.getByText("-5,67%")).toBeInTheDocument()
    expect(screen.getByText("-1,23%")).toBeInTheDocument()

    const trendElement = screen.getByText("-1,23%").closest("div")
    expect(trendElement).toHaveClass("text-red-600")
  })

  it("shows unit when provided", () => {
    render(
      <MetricCard title="Recovery Time" value={45} unit="days" format="number" precision={0} />
    )

    expect(screen.getByText("45 days")).toBeInTheDocument()
  })

  it("is accessible", () => {
    render(<MetricCard title="Test Metric" value={123.45} />)

    // Should have proper heading structure
    const heading = screen.getByRole("heading", { name: "Test Metric" })
    expect(heading).toBeInTheDocument()

    // Should have article element
    const article = screen.getByRole("article")
    expect(article).toBeInTheDocument()
  })

  it("handles zero values correctly", () => {
    render(<MetricCard title="Zero Value" value={0} format="percentage" />)

    expect(screen.getByText("0,00%")).toBeInTheDocument()
  })

  it("handles very large numbers", () => {
    render(<MetricCard title="Large Number" value={1234567.89} format="currency" />)

    expect(screen.getByText("R$ 1.234.567,89")).toBeInTheDocument()
  })

  it("applies custom className", () => {
    render(<MetricCard title="Custom Style" value={42} className="custom-metric-card" />)

    const card = screen.getByRole("article")
    expect(card).toHaveClass("custom-metric-card")
  })
})
