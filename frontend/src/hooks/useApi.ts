/**
 * React Query hooks for API integration
 * Provides data fetching with caching, loading states, and error handling
 */

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api"

// Query keys for caching
export const queryKeys = {
  funds: ["funds"] as const,
  fundPerformance: (cnpj: string) => ["fund", "performance", cnpj] as const,
  fundDaily: (cnpj: string) => ["fund", "daily", cnpj] as const,
  fundExplanations: (cnpj: string) => ["fund", "explanations", cnpj] as const,
}

// Hooks
export const useFunds = () => {
  return useQuery({
    queryKey: queryKeys.funds,
    queryFn: apiClient.getFunds,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export const useFundPerformance = (cnpj: string) => {
  return useQuery({
    queryKey: queryKeys.fundPerformance(cnpj),
    queryFn: () => apiClient.getFundPerformance(cnpj),
    enabled: Boolean(cnpj), // Only fetch if cnpj is provided
    staleTime: 30 * 1000, // 30 seconds
  })
}

export const useFundDaily = (cnpj: string) => {
  return useQuery({
    queryKey: queryKeys.fundDaily(cnpj),
    queryFn: () => apiClient.getFundDaily(cnpj),
    enabled: Boolean(cnpj),
    staleTime: 60 * 1000, // 1 minute
  })
}

export const useFundExplanations = (cnpj: string) => {
  return useQuery({
    queryKey: queryKeys.fundExplanations(cnpj),
    queryFn: () => apiClient.getFundExplanations(cnpj),
    enabled: Boolean(cnpj),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}