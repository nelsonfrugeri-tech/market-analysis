import { AlertCircle } from "lucide-react"
import { MetricCard } from "@/components/ui/metric-card"
import { MetricsSection } from "@/components/ui/metrics-section"
import type { PerformanceMetrics } from "@/types/api"
import type { PerformanceCardProps } from "@/types/components"

// Type for metric definitions
interface MetricDefinition {
  key: keyof PerformanceMetrics
  title: string
  format: "percentage" | "ratio" | "number" | "currency"
  unit?: string
  precision?: number
  tooltip: string
}

// Metric definitions with tooltips
const PERFORMANCE_METRICS: MetricDefinition[] = [
  {
    key: "totalReturn" as const,
    title: "Retorno Total",
    format: "percentage" as const,
    tooltip:
      "Retorno total acumulado no período selecionado, considerando todos os rendimentos e variações do valor da cota.",
  },
  {
    key: "annualizedReturn" as const,
    title: "Retorno Anualizado",
    format: "percentage" as const,
    tooltip:
      "Retorno anualizado do fundo, calculado com base na performance histórica e projetado para um ano completo.",
  },
  {
    key: "monthlyReturn" as const,
    title: "Retorno Mensal",
    format: "percentage" as const,
    tooltip:
      "Retorno obtido no último mês completo, útil para acompanhar a performance recente do fundo.",
  },
  {
    key: "yearToDate" as const,
    title: "Year-to-Date",
    format: "percentage" as const,
    tooltip: "Retorno acumulado desde o início do ano atual até a data mais recente disponível.",
  },
  {
    key: "volatility" as const,
    title: "Volatilidade",
    format: "percentage" as const,
    tooltip:
      "Medida do grau de variação dos retornos. Maior volatilidade indica maior risco e maior potencial de ganhos/perdas.",
  },
  {
    key: "sharpeRatio" as const,
    title: "Índice Sharpe",
    format: "ratio" as const,
    tooltip:
      "Mede o retorno ajustado ao risco. Valores acima de 1,0 são considerados bons, acima de 2,0 são excelentes.",
  },
  {
    key: "maxDrawdown" as const,
    title: "Drawdown Máximo",
    format: "percentage" as const,
    tooltip:
      "Maior perda acumulada em um período contínuo. Indica o pior cenário de perdas que o investidor teria enfrentado.",
  },
  {
    key: "recoveryTime" as const,
    title: "Tempo de Recuperação",
    format: "number" as const,
    precision: 0,
    unit: "dias",
    tooltip:
      "Número de dias necessários para recuperar as perdas do drawdown máximo. Períodos menores indicam maior resiliência.",
  },
]

// Error Alert component
const ErrorAlert = ({ error }: { error: string }) => (
  <div
    role="alert"
    className="flex items-center space-x-2 p-4 text-red-600 bg-red-50 border border-red-200 rounded-md"
  >
    <AlertCircle className="h-5 w-5 flex-shrink-0" />
    <span className="text-sm font-medium">{error}</span>
  </div>
)

export const PerformanceSection = ({
  metrics,
  period,
  isLoading = false,
  error = null,
  className,
  ...props
}: PerformanceCardProps) => {
  const description = `Indicadores de rentabilidade e performance para ${period}`

  return (
    <MetricsSection title="Performance" description={description} className={className} {...props}>
      {error ? (
        <ErrorAlert error={error} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {PERFORMANCE_METRICS.map((metric) => {
            const { key, title, format, unit, tooltip, precision } = metric
            const value = metrics[key]

            // Handle special formatting cases
            const getFormattedProps = () => {
              const baseProps = {
                title,
                value,
                format,
                tooltip,
                isLoading,
                unit,
                precision,
              }

              // Add trend information if we had historical data
              // In a real app, we would calculate trends from previous periods
              if (key === "totalReturn" && !isLoading && value > 0) {
                return {
                  ...baseProps,
                  trend: "up" as const,
                  // trendValue would come from period-over-period comparison
                }
              }

              if (key === "maxDrawdown" && !isLoading && value < 0) {
                return {
                  ...baseProps,
                  trend: "down" as const,
                  // For drawdown, "up" trend would mean less negative (better)
                }
              }

              return baseProps
            }

            return <MetricCard key={key} {...getFormattedProps()} />
          })}
        </div>
      )}
    </MetricsSection>
  )
}
