import { HelpCircle, TrendingDown, TrendingUp } from "lucide-react"
import type { ReactNode } from "react"

import { formatCurrency, formatNumber, formatPercentage, getTrendColor } from "@/lib/formatters"
import { cn } from "@/lib/utils"
import type { MetricCardProps } from "@/types/components"

interface TooltipProps {
  content: string
  children: ReactNode
}

// Simple tooltip implementation (will be replaced with shadcn/ui tooltip later)
const Tooltip = ({ content, children }: TooltipProps) => (
  <div className="group relative">
    {children}
    <div className="invisible group-hover:visible absolute z-10 w-64 p-2 text-sm text-white bg-gray-900 rounded-md shadow-lg bottom-full left-1/2 transform -translate-x-1/2 mb-2">
      {content}
      <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900" />
    </div>
  </div>
)

// Loading skeleton component
const MetricCardSkeleton = () => (
  <div data-testid="metric-card-skeleton" className="space-y-2">
    <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    <div className="h-3 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
  </div>
)

export const MetricCard = ({
  title,
  value,
  unit = "",
  trend,
  trendValue,
  tooltip,
  isLoading = false,
  format = "number",
  precision = 2,
  className,
  ...props
}: MetricCardProps) => {
  // Format the main value
  const formatMainValue = (): string => {
    switch (format) {
      case "percentage":
        return formatPercentage(value, { precision })
      case "currency":
        return formatCurrency(value, { precision })
      case "ratio":
        return formatNumber(value, { precision })
      default:
        return formatNumber(value, { precision, showUnit: Boolean(unit), unit })
    }
  }

  // Format the trend value
  const formatTrendValue = (): string | null => {
    if (trendValue === undefined) return null

    const showSign = true
    switch (format) {
      case "percentage":
        return formatPercentage(trendValue, { precision, showSign })
      case "currency":
        return formatCurrency(trendValue, { precision, showSign })
      default:
        return formatNumber(trendValue, { precision, showSign, showUnit: Boolean(unit), unit })
    }
  }

  // Get trend icon
  const getTrendIcon = () => {
    if (!trend || !trendValue) return null

    const iconClass = cn(
      "h-4 w-4",
      getTrendColor(trend === "up" ? "up" : trend === "down" ? "down" : "neutral")
    )

    if (trend === "up") {
      return <TrendingUp className={iconClass} />
    } else if (trend === "down") {
      return <TrendingDown className={iconClass} />
    }

    return null
  }

  const formattedMainValue = formatMainValue()
  const formattedTrendValue = formatTrendValue()
  const trendIcon = getTrendIcon()
  const trendColorClass = trend
    ? getTrendColor(trend === "up" ? "up" : trend === "down" ? "down" : "neutral")
    : ""

  if (isLoading) {
    return (
      <article
        className={cn(
          "p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm",
          className
        )}
        {...props}
      >
        <MetricCardSkeleton />
      </article>
    )
  }

  return (
    <article
      className={cn(
        "p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm transition-colors",
        className
      )}
      {...props}
    >
      <div className="space-y-2">
        {/* Header with title and optional tooltip */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-300">{title}</h3>
          {tooltip && (
            <Tooltip content={tooltip}>
              <HelpCircle
                data-testid="help-icon"
                className="h-4 w-4 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 cursor-help"
              />
            </Tooltip>
          )}
        </div>

        {/* Main value */}
        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {formattedMainValue}
        </div>

        {/* Trend indicator */}
        {(trendIcon || formattedTrendValue) && (
          <div className={cn("flex items-center space-x-1 text-sm", trendColorClass)}>
            {trendIcon}
            {formattedTrendValue && <span>{formattedTrendValue}</span>}
          </div>
        )}
      </div>
    </article>
  )
}
