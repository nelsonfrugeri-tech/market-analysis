/**
 * API Types for Market Analysis Dashboard
 * Defines TypeScript contracts for all API endpoints
 */

// Base types
export interface DateRange {
  start: string // ISO date
  end: string // ISO date
}

export interface Fund {
  cnpj: string
  name: string
  short_name: string
  fund_type: string
  manager: string
  benchmark: string
  status: string
}

// Filter types
export interface DashboardFilters {
  period: DateRange
  categories: string[]
  benchmarks: BenchmarkType[]
  granularity: "daily" | "weekly" | "monthly"
}

// Benchmark types
export type BenchmarkType = "CDI" | "SELIC" | "IPCA" | "CDB" | "POUPANCA"

export interface BenchmarkData {
  type: BenchmarkType
  value: number
  date: string
  annualized: number
}

// Performance Metrics (Section 1)
export interface PerformanceMetrics {
  totalReturn: number // % total return
  annualizedReturn: number // % annualized
  monthlyReturn: number // % last month
  yearToDate: number // % YTD
  volatility: number // % annualized volatility
  sharpeRatio: number // risk-adjusted return
  maxDrawdown: number // % worst loss
  recoveryTime: number // days to recover from max drawdown
}

// Risk Metrics (Section 2)
export interface RiskMetrics {
  valueAtRisk: number // % VaR 95%
  conditionalVaR: number // % CVaR (expected shortfall)
  beta: number // market correlation
  standardDeviation: number // % price volatility
  downDeviation: number // % downside volatility
  sortinoRatio: number // downside risk-adjusted return
  calmarRatio: number // return vs max drawdown
  treynorRatio: number // return per unit of systematic risk
}

// Efficiency Metrics (Section 3)
export interface EfficiencyMetrics {
  informationRatio: number // active return vs tracking error
  trackingError: number // % deviation from benchmark
  activeReturn: number // % outperformance vs benchmark
  rSquared: number // % correlation with benchmark
  alpha: number // % excess return vs expected
  capture_up: number // % upside capture vs benchmark
  capture_down: number // % downside capture vs benchmark
  selectivity: number // stock selection skill
}

// Consistency Metrics (Section 4)
export interface ConsistencyMetrics {
  positiveMonths: number // % of profitable months
  winRate: number // % winning periods
  avgWin: number // % average winning period
  avgLoss: number // % average losing period
  winLossRatio: number // avg win / avg loss
  consistency: number // % periods beating benchmark
  streak_positive: number // longest winning streak (periods)
  streak_negative: number // longest losing streak (periods)
}

// Benchmark Comparison (Section 5)
export interface BenchmarkComparison {
  fund_return: number
  benchmark_return: number
  benchmark_type: BenchmarkType
  outperformance: number // fund - benchmark
  correlation: number // correlation coefficient
  tracking_error: number // standard deviation of outperformance
  information_ratio: number // outperformance / tracking_error
}

// Monthly Evolution Data (Section 6)
export interface MonthlyEvolution {
  date: string // YYYY-MM format
  nav: number // Net Asset Value
  return_month: number // % monthly return
  return_accumulated: number // % accumulated return
  benchmark_return: number // % benchmark return for comparison
  outperformance: number // % vs benchmark
  volatility: number // % monthly volatility
}

// Complete Dashboard Data Response
export interface DashboardData {
  fund: Fund
  period: DateRange
  performance: PerformanceMetrics
  risk: RiskMetrics
  efficiency: EfficiencyMetrics
  consistency: ConsistencyMetrics
  benchmarks: BenchmarkComparison[]
  monthlyEvolution: MonthlyEvolution[]
  lastUpdated: string // ISO timestamp
}

// Chart-specific data types
export interface NAVEvolutionData {
  date: string
  nav: number
  benchmark: number
  type: BenchmarkType
}

export interface MonthlyReturnsData {
  month: string
  fund: number
  benchmark: number
  outperformance: number
}

// API Error Response
export interface APIError {
  message: string
  code: string
  details?: Record<string, unknown>
}

// API Success Response wrapper
export interface APIResponse<T> {
  data: T
  success: true
  timestamp: string
}

export interface APIErrorResponse {
  error: APIError
  success: false
  timestamp: string
}

// API Endpoints (6 endpoints as mentioned in architecture)
export interface ApiEndpoints {
  "/api/funds": {
    GET: {
      response: APIResponse<Fund[]>
    }
  }

  "/api/dashboard/{cnpj}": {
    GET: {
      params: { cnpj: string }
      query?: Partial<DashboardFilters>
      response: APIResponse<DashboardData>
    }
  }

  "/api/performance/{cnpj}": {
    GET: {
      params: { cnpj: string }
      query?: Partial<DashboardFilters>
      response: APIResponse<PerformanceMetrics>
    }
  }

  "/api/benchmarks": {
    GET: {
      query?: { types?: BenchmarkType[]; period?: DateRange }
      response: APIResponse<BenchmarkData[]>
    }
  }

  "/api/charts/nav/{cnpj}": {
    GET: {
      params: { cnpj: string }
      query?: { benchmark?: BenchmarkType; period?: DateRange }
      response: APIResponse<NAVEvolutionData[]>
    }
  }

  "/api/collect": {
    POST: {
      response: APIResponse<{ message: string; updated_at: string }>
    }
  }
}
