/**
 * Fund Selector Component
 * Dropdown for selecting which fund to view in the dashboard
 */

import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Fund } from "@/types/api"

interface FundSelectorProps {
  funds: Fund[]
  selectedFund: Fund | null
  onSelectFund: (fund: Fund) => void
  isLoading?: boolean
  error?: string | null
  className?: string
}

export const FundSelector = ({
  funds,
  selectedFund,
  onSelectFund,
  isLoading = false,
  error = null,
  className,
}: FundSelectorProps) => {
  if (error) {
    return (
      <div className={cn("p-4 text-red-600 bg-red-50 border border-red-200 rounded-md", className)}>
        <span className="text-sm font-medium">Erro ao carregar fundos: {error}</span>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className={cn("space-y-2", className)}>
        <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-10 w-full bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
    )
  }

  return (
    <div className={cn("space-y-2", className)}>
      <label htmlFor="fund-selector" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Selecionar Fundo
      </label>
      <div className="relative">
        <select
          id="fund-selector"
          value={selectedFund?.cnpj || ""}
          onChange={(e) => {
            const fund = funds.find(f => f.cnpj === e.target.value)
            if (fund) {
              onSelectFund(fund)
            }
          }}
          className="appearance-none w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Selecione um fundo...</option>
          {funds.map((fund) => (
            <option key={fund.cnpj} value={fund.cnpj}>
              {fund.short_name || fund.name} - {fund.fund_type}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
      </div>
      {selectedFund && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium">CNPJ:</span> {selectedFund.cnpj}
          <span className="mx-2">•</span>
          <span className="font-medium">Gestor:</span> {selectedFund.manager}
        </div>
      )}
    </div>
  )
}