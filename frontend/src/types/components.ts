/**
 * Component Types for Market Analysis Dashboard
 * Defines TypeScript contracts for UI components and application state
 */

import type { ReactNode } from "react"
import type {
  BenchmarkType,
  ConsistencyMetrics,
  DashboardFilters,
  EfficiencyMetrics,
  MonthlyEvolution,
  PerformanceMetrics,
  RiskMetrics,
} from "./api"

// Common component props
export interface BaseComponentProps {
  className?: string
  children?: ReactNode
}

// Loading and Error states
export interface LoadingState {
  isLoading: boolean
  error: string | null
}

export interface AsyncComponentProps extends BaseComponentProps, LoadingState {}

// Metric Card Components
export interface MetricCardProps extends BaseComponentProps {
  title: string
  value: number
  unit?: string
  trend?: "up" | "down" | "neutral"
  trendValue?: number
  tooltip?: string
  isLoading?: boolean
  format?: "percentage" | "number" | "currency" | "ratio"
  precision?: number
}

export interface MetricsSectionProps extends BaseComponentProps {
  title: string
  description?: string
  isCollapsible?: boolean
  isExpanded?: boolean
  onToggle?: () => void
}

// Performance Section
export interface PerformanceCardProps extends AsyncComponentProps {
  metrics: PerformanceMetrics
  period: string
}

// Risk Section
export interface RiskCardProps extends AsyncComponentProps {
  metrics: RiskMetrics
  period: string
}

// Efficiency Section
export interface EfficiencyCardProps extends AsyncComponentProps {
  metrics: EfficiencyMetrics
  period: string
}

// Consistency Section
export interface ConsistencyCardProps extends AsyncComponentProps {
  metrics: ConsistencyMetrics
  period: string
}

// Filter Components
export interface FilterSidebarProps extends BaseComponentProps {
  filters: DashboardFilters
  onFiltersChange: (filters: Partial<DashboardFilters>) => void
  availableBenchmarks: BenchmarkType[]
  availableCategories: string[]
  isOpen: boolean
  onToggle: () => void
}

export interface DateRangePickerProps extends BaseComponentProps {
  value: { start: string; end: string }
  onChange: (range: { start: string; end: string }) => void
  maxDate?: string
  minDate?: string
}

export interface MultiSelectProps extends BaseComponentProps {
  label: string
  options: Array<{ label: string; value: string }>
  selectedValues: string[]
  onSelectionChange: (values: string[]) => void
  placeholder?: string
}

// Chart Components
export interface ChartContainerProps extends AsyncComponentProps {
  title: string
  height?: number
  width?: number
}

export interface NAVChartProps extends ChartContainerProps {
  data: Array<{
    date: string
    nav: number
    benchmark?: number
    benchmarkType?: BenchmarkType
  }>
  showBenchmark?: boolean
  currency?: string
}

export interface MonthlyReturnsChartProps extends ChartContainerProps {
  data: MonthlyEvolution[]
  benchmarkType?: BenchmarkType
  showOutperformance?: boolean
}

export interface ComparisonBarChartProps extends ChartContainerProps {
  data: Array<{
    metric: string
    fund: number
    benchmark: number
    unit: string
  }>
  orientation?: "horizontal" | "vertical"
}

// Dashboard Layout Components
export interface DashboardLayoutProps extends BaseComponentProps {
  fundName: string
  cnpj: string
  lastUpdated?: string
  onRefresh?: () => void
  refreshing?: boolean
}

export interface DashboardHeaderProps extends BaseComponentProps {
  fundName: string
  cnpj: string
  lastUpdated?: string
  onRefresh?: () => void
  onFiltersToggle?: () => void
  refreshing?: boolean
}

// Table Components (for detailed data)
export interface DataTableProps<T> extends BaseComponentProps {
  data: T[]
  columns: Array<{
    key: keyof T
    title: string
    sortable?: boolean
    format?: "number" | "percentage" | "currency" | "date"
    precision?: number
  }>
  sortBy?: keyof T
  sortDirection?: "asc" | "desc"
  onSort?: (key: keyof T, direction: "asc" | "desc") => void
  pagination?: {
    page: number
    pageSize: number
    total: number
    onPageChange: (page: number) => void
  }
  isLoading?: boolean
  emptyMessage?: string
}

// Tooltip and Help Components
export interface TooltipProps extends BaseComponentProps {
  content: ReactNode
  trigger: ReactNode
  side?: "top" | "right" | "bottom" | "left"
  delay?: number
}

export interface HelpIconProps extends BaseComponentProps {
  tooltip: string
  size?: "sm" | "md" | "lg"
}

// Theme and Styling
export interface ThemeToggleProps extends BaseComponentProps {
  variant?: "icon" | "button" | "switch"
}

// App State Types
export interface AppState {
  filters: DashboardFilters
  ui: {
    sidebarOpen: boolean
    theme: "light" | "dark" | "system"
    expandedSections: string[]
  }
  cache: {
    lastFetch: string | null
    autoRefresh: boolean
    refreshInterval: number // minutes
  }
}

export interface UIActions {
  toggleSidebar: () => void
  setTheme: (theme: "light" | "dark" | "system") => void
  toggleSection: (sectionId: string) => void
  updateFilters: (filters: Partial<DashboardFilters>) => void
  resetFilters: () => void
}

// Form Components (for settings/configuration)
export interface FormFieldProps extends BaseComponentProps {
  label: string
  name: string
  type?: "text" | "number" | "email" | "password" | "select" | "checkbox"
  placeholder?: string
  required?: boolean
  disabled?: boolean
  error?: string
  helpText?: string
}

export interface FormProps extends BaseComponentProps {
  onSubmit: (data: Record<string, unknown>) => void
  isSubmitting?: boolean
  resetOnSubmit?: boolean
}

// Export/Import Components
export interface ExportButtonProps extends BaseComponentProps {
  data: unknown
  filename: string
  format: "csv" | "xlsx" | "pdf" | "json"
  disabled?: boolean
}

// Responsive and Accessibility
export type Breakpoint = "sm" | "md" | "lg" | "xl" | "2xl"

export interface ResponsiveProps {
  hideOn?: Breakpoint[]
  showOn?: Breakpoint[]
}

export interface AccessibilityProps {
  "aria-label"?: string
  "aria-describedby"?: string
  "aria-expanded"?: boolean
  "aria-hidden"?: boolean
  role?: string
  tabIndex?: number
}
