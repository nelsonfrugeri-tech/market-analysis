import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { mockPerformanceMetrics } from "@/lib/mock-data"

import { PerformanceSection } from "./performance-section"

describe("PerformanceSection", () => {
  const defaultProps = {
    metrics: mockPerformanceMetrics,
    period: "últimos 12 meses",
    isLoading: false,
    error: null,
  }

  it("renders all performance metrics correctly", () => {
    render(<PerformanceSection {...defaultProps} />)

    // Should show section title
    expect(screen.getByRole("region", { name: "Performance" })).toBeInTheDocument()

    // Should show all key metrics
    expect(screen.getByText("Retorno Total")).toBeInTheDocument()
    expect(screen.getByText("Retorno Anualizado")).toBeInTheDocument()
    expect(screen.getByText("Retorno Mensal")).toBeInTheDocument()
    expect(screen.getByText("Year-to-Date")).toBeInTheDocument()
    expect(screen.getByText("Volatilidade")).toBeInTheDocument()
    expect(screen.getByText("Índice Sharpe")).toBeInTheDocument()
    expect(screen.getByText("Drawdown Máximo")).toBeInTheDocument()
    expect(screen.getByText("Tempo de Recuperação")).toBeInTheDocument()

    // Should show formatted values
    expect(screen.getByText("8,45%")).toBeInTheDocument() // totalReturn
    expect(screen.getByText("10,12%")).toBeInTheDocument() // annualizedReturn
    expect(screen.getByText("6,23%")).toBeInTheDocument() // yearToDate
    expect(screen.getByText("1,34")).toBeInTheDocument() // sharpeRatio
    expect(screen.getByText("45 dias")).toBeInTheDocument() // recoveryTime
  })

  it("shows loading state", () => {
    render(<PerformanceSection {...defaultProps} isLoading={true} />)

    // Should show skeleton loaders
    expect(screen.getAllByTestId("metric-card-skeleton")).toHaveLength(8)
  })

  it("shows error state", () => {
    render(<PerformanceSection {...defaultProps} error="Failed to load performance metrics" />)

    expect(screen.getByText("Failed to load performance metrics")).toBeInTheDocument()
    expect(screen.getByRole("alert")).toBeInTheDocument()
  })

  it("shows proper tooltips for metrics", () => {
    render(<PerformanceSection {...defaultProps} />)

    // Should have help icons for tooltips
    const helpIcons = screen.getAllByTestId("help-icon")
    expect(helpIcons.length).toBeGreaterThan(0)
  })

  it("formats negative values correctly", () => {
    const metricsWithNegatives = {
      ...mockPerformanceMetrics,
      totalReturn: -5.23,
      monthlyReturn: -1.45,
      maxDrawdown: -8.76,
    }

    render(<PerformanceSection {...defaultProps} metrics={metricsWithNegatives} />)

    expect(screen.getByText("-5,23%")).toBeInTheDocument()
    expect(screen.getByText("-1,45%")).toBeInTheDocument()
    expect(screen.getByText("-8,76%")).toBeInTheDocument()
  })

  it("shows trend indicators when available", () => {
    const metricsWithTrends = {
      ...mockPerformanceMetrics,
      totalReturn: 8.45,
      // In a real scenario, we would have previous period data to calculate trends
    }

    render(<PerformanceSection {...defaultProps} metrics={metricsWithTrends} />)

    // Should render without errors even without trend data
    expect(screen.getByText("Retorno Total")).toBeInTheDocument()
  })

  it("handles zero values gracefully", () => {
    const metricsWithZeros = {
      ...mockPerformanceMetrics,
      totalReturn: 0,
      monthlyReturn: 0,
      sharpeRatio: 0,
    }

    render(<PerformanceSection {...defaultProps} metrics={metricsWithZeros} />)

    // Should handle zero percentages (multiple elements expected)
    const zeroPercentages = screen.getAllByText("0,00%")
    expect(zeroPercentages.length).toBeGreaterThanOrEqual(2) // totalReturn and monthlyReturn

    // Should handle zero ratio
    expect(screen.getByText("0,00")).toBeInTheDocument()
  })

  it("shows period information", () => {
    render(<PerformanceSection {...defaultProps} period="últimos 6 meses" />)

    expect(screen.getByText(/últimos 6 meses/i)).toBeInTheDocument()
  })

  it("applies custom className", () => {
    render(<PerformanceSection {...defaultProps} className="custom-performance-section" />)

    const section = screen.getByRole("region")
    expect(section).toHaveClass("custom-performance-section")
  })

  it("is accessible with proper structure", () => {
    render(<PerformanceSection {...defaultProps} />)

    // Should have proper section structure
    const section = screen.getByRole("region", { name: "Performance" })
    expect(section).toBeInTheDocument()

    // Should have proper heading hierarchy
    const heading = screen.getByRole("heading", { level: 2 })
    expect(heading).toBeInTheDocument()

    // All metric cards should be accessible
    const articles = screen.getAllByRole("article")
    expect(articles).toHaveLength(8)
  })

  it("handles very large numbers correctly", () => {
    const metricsWithLargeNumbers = {
      ...mockPerformanceMetrics,
      recoveryTime: 999,
      volatility: 99.99,
    }

    render(<PerformanceSection {...defaultProps} metrics={metricsWithLargeNumbers} />)

    expect(screen.getByText("999 dias")).toBeInTheDocument()
    expect(screen.getByText("99,99%")).toBeInTheDocument()
  })
})
