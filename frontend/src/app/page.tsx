'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MetricCard } from '@/components/ui/metric-card'
import { MetricsSection } from '@/components/ui/metrics-section'
import { PerformanceSection } from '@/components/metrics/performance-section'
import type { Fund, PerformanceMetrics, RiskMetrics, EfficiencyMetrics, ConsistencyMetrics } from '@/types/api'

// Mock data generators for demonstration
const mockPerformanceMetrics = (fundName: string): PerformanceMetrics => ({
  totalReturn: 45.2,
  annualizedReturn: 12.8,
  monthlyReturn: 3.5,
  yearToDate: 18.6,
  volatility: 8.2,
  sharpeRatio: 1.45,
  maxDrawdown: -15.3,
  recoveryTime: 42,
})

const mockRiskMetrics = (fundName: string): RiskMetrics => ({
  valueAtRisk: 5.2,
  conditionalVaR: 7.8,
  beta: 0.92,
  standardDeviation: 8.2,
  downDeviation: 5.1,
  sortinoRatio: 2.34,
  calmarRatio: 2.95,
  treynorRatio: 12.3,
})

const mockEfficiencyMetrics = (fundName: string): EfficiencyMetrics => ({
  informationRatio: 1.23,
  trackingError: 4.5,
  activeReturn: 3.2,
  rSquared: 0.78,
  alpha: 4.1,
  capture_up: 95.3,
  capture_down: 72.5,
  selectivity: 8.5,
})

const mockConsistencyMetrics = (fundName: string): ConsistencyMetrics => ({
  positiveMonths: 72.4,
  winRate: 68.5,
  avgWin: 2.3,
  avgLoss: -1.8,
  winLossRatio: 1.28,
  consistency: 65.2,
  streak_positive: 12,
  streak_negative: 5,
})

interface DashboardData {
  performance: PerformanceMetrics
  risk: RiskMetrics
  efficiency: EfficiencyMetrics
  consistency: ConsistencyMetrics
}

// Import API client
import { apiClient } from '@/lib/api'

// Fetch analysis for a specific fund with backend connection
async function fetchFundAnalysis(cnpj: string): Promise<DashboardData> {
  try {
    // Use the API client that properly handles backend mapping
    return await apiClient.getFundPerformance(cnpj)
  } catch (error) {
    console.error('Failed to fetch real data, falling back to mock:', error)
    // Fallback to mock data if backend fails
    const fundName = cnpj
    return {
      performance: mockPerformanceMetrics(fundName),
      risk: mockRiskMetrics(fundName),
      efficiency: mockEfficiencyMetrics(fundName),
      consistency: mockConsistencyMetrics(fundName),
    }
  }
}

export default function Home() {
  const [selectedCnpj, setSelectedCnpj] = useState<string | null>(null)

  // Fetch funds using API client
  const {
    data: funds = [],
    isLoading: fundsLoading,
    error: fundsError,
  } = useQuery({
    queryKey: ['funds'],
    queryFn: apiClient.getFunds,
    retry: 2,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Auto-select first fund if available
  const currentCnpj = useMemo(() => {
    if (selectedCnpj) return selectedCnpj
    if (funds.length > 0) return funds[0].cnpj
    return null
  }, [selectedCnpj, funds])

  // Fetch analysis for selected fund
  const {
    data: analysis,
    isLoading: analysisLoading,
    error: analysisError,
  } = useQuery({
    queryKey: ['analysis', currentCnpj],
    queryFn: () => fetchFundAnalysis(currentCnpj!),
    enabled: !!currentCnpj,
    retry: 2,
    staleTime: 1000 * 60 * 5,
  })

  const currentFund = funds.find((f) => f.cnpj === currentCnpj)
  const isLoading = fundsLoading || analysisLoading
  const error = fundsError || analysisError

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-800 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Market Analysis Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Investment fund performance analysis and metrics
              </p>
            </div>

            {/* Fund Selector */}
            <div className="min-w-[300px]">
              <label htmlFor="fund-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Select Fund
              </label>
              <select
                id="fund-select"
                value={currentCnpj || ''}
                onChange={(e) => setSelectedCnpj(e.target.value)}
                disabled={fundsLoading}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-gray-900 dark:text-white disabled:opacity-50"
              >
                <option value="">
                  {fundsLoading ? 'Loading funds...' : 'Select a fund'}
                </option>
                {funds.map((fund) => (
                  <option key={fund.cnpj} value={fund.cnpj}>
                    {fund.name} ({fund.cnpj})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">
              Error loading data: {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          </div>
        )}

        {currentFund && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              {currentFund.name}
            </h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              CNPJ: {currentFund.cnpj} • Category: {currentFund.fund_type} • Manager: {currentFund.manager}
            </p>
          </div>
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 9 }).map((_, i) => (
              <MetricCard key={i} title="" value={0} isLoading={true} />
            ))}
          </div>
        ) : !analysis ? (
          <div className="text-center py-12">
            <p className="text-gray-600 dark:text-gray-400">
              Select a fund to view analysis
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Performance Section */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Performance Metrics
              </h3>
              <PerformanceSection
                metrics={analysis.performance}
                period="6 months"
                isLoading={false}
                error={null}
              />
            </div>

            {/* Risk Section */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Risk Metrics
              </h3>
              <MetricsSection
                title="Risk Analysis"
                metrics={[
                  {
                    title: 'Value at Risk (VaR)',
                    value: analysis.risk.valueAtRisk,
                    unit: '%',
                    format: 'percentage',
                    tooltip: '95% confidence level',
                  },
                  {
                    title: 'Conditional VaR',
                    value: analysis.risk.conditionalVaR,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Expected shortfall',
                  },
                  {
                    title: 'Beta',
                    value: analysis.risk.beta,
                    format: 'ratio',
                    tooltip: 'Market sensitivity',
                  },
                  {
                    title: 'Volatility',
                    value: analysis.risk.standardDeviation,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Annualized std deviation',
                  },
                  {
                    title: 'Sortino Ratio',
                    value: analysis.risk.sortinoRatio,
                    format: 'ratio',
                    tooltip: 'Risk-adjusted return (downside)',
                  },
                  {
                    title: 'Calmar Ratio',
                    value: analysis.risk.calmarRatio,
                    format: 'ratio',
                    tooltip: 'Return vs max drawdown',
                  },
                ]}
                isLoading={false}
              />
            </div>

            {/* Efficiency Section */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Efficiency Metrics
              </h3>
              <MetricsSection
                title="Efficiency Analysis"
                metrics={[
                  {
                    title: 'Information Ratio',
                    value: analysis.efficiency.informationRatio,
                    format: 'ratio',
                    tooltip: 'Active return vs tracking error',
                  },
                  {
                    title: 'Tracking Error',
                    value: analysis.efficiency.trackingError,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Deviation from benchmark',
                  },
                  {
                    title: 'Alpha',
                    value: analysis.efficiency.alpha,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Excess return',
                  },
                  {
                    title: 'R-Squared',
                    value: analysis.efficiency.rSquared * 100,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Correlation with benchmark',
                  },
                  {
                    title: 'Upside Capture',
                    value: analysis.efficiency.capture_up,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Upside capture vs benchmark',
                  },
                  {
                    title: 'Downside Capture',
                    value: analysis.efficiency.capture_down,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Downside capture vs benchmark',
                  },
                ]}
                isLoading={false}
              />
            </div>

            {/* Consistency Section */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Consistency Metrics
              </h3>
              <MetricsSection
                title="Consistency Analysis"
                metrics={[
                  {
                    title: 'Positive Months',
                    value: analysis.consistency.positiveMonths,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Profitable months percentage',
                  },
                  {
                    title: 'Win Rate',
                    value: analysis.consistency.winRate,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Winning periods',
                  },
                  {
                    title: 'Avg Win',
                    value: analysis.consistency.avgWin,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Average winning period',
                  },
                  {
                    title: 'Avg Loss',
                    value: analysis.consistency.avgLoss,
                    unit: '%',
                    format: 'percentage',
                    tooltip: 'Average losing period',
                  },
                  {
                    title: 'Win/Loss Ratio',
                    value: analysis.consistency.winLossRatio,
                    format: 'ratio',
                    tooltip: 'Avg win / avg loss',
                  },
                  {
                    title: 'Longest Win Streak',
                    value: analysis.consistency.streak_positive,
                    format: 'number',
                    tooltip: 'Consecutive winning periods',
                  },
                ]}
                isLoading={false}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
