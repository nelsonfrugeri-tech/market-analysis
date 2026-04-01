import { ChevronDown, ChevronUp } from "lucide-react"

import { cn } from "@/lib/utils"
import type { MetricsSectionProps } from "@/types/components"

export const MetricsSection = ({
  title,
  description,
  isCollapsible = false,
  isExpanded = true,
  onToggle,
  className,
  children,
  ...props
}: MetricsSectionProps) => {
  const handleToggle = () => {
    if (isCollapsible && onToggle) {
      onToggle()
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      handleToggle()
    }
  }

  return (
    <section
      aria-labelledby={`${title.toLowerCase().replace(/\s+/g, "-")}-heading`}
      className={cn(
        "bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm",
        className
      )}
      {...props}
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        {isCollapsible ? (
          <button
            type="button"
            onClick={handleToggle}
            onKeyDown={handleKeyDown}
            aria-expanded={isExpanded}
            aria-controls={`${title.toLowerCase().replace(/\s+/g, "-")}-content`}
            className="w-full flex items-center justify-between text-left hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md p-2 -m-2 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <div className="min-w-0 flex-1">
              <h2
                id={`${title.toLowerCase().replace(/\s+/g, "-")}-heading`}
                className="text-lg font-semibold text-gray-900 dark:text-gray-100"
              >
                {title}
              </h2>
              {description && (
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{description}</p>
              )}
            </div>
            <div className="ml-4 flex-shrink-0">
              {isExpanded ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </div>
          </button>
        ) : (
          <div>
            <h2
              id={`${title.toLowerCase().replace(/\s+/g, "-")}-heading`}
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              {title}
            </h2>
            {description && (
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      {(!isCollapsible || isExpanded) && (
        <div id={`${title.toLowerCase().replace(/\s+/g, "-")}-content`} className="p-6">
          {children}
        </div>
      )}
    </section>
  )
}
