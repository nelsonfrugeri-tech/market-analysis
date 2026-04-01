'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp, TrendingDown, Users, DollarSign, Activity,
  ArrowUpRight, ArrowDownRight, Calendar, RefreshCw, BarChart3,
  Shield, Target, Zap,
} from 'lucide-react'
import { apiClient } from '@/lib/api'
import type { Fund } from '@/types/api'
import { cn } from '@/lib/utils'

// ── Utility formatters ──

function fmtPct(v: number, decimals = 2): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(decimals)}%`
}

function fmtNum(v: number, decimals = 2): string {
  return v.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function fmtCompact(v: number): string {
  if (v >= 1_000_000_000) return `R$ ${(v / 1_000_000_000).toFixed(1)}B`
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `R$ ${(v / 1_000).toFixed(1)}K`
  return `R$ ${v.toFixed(0)}`
}

function fmtDate(d: string): string {
  return new Date(`${d}T12:00:00`).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

// ── Stat Card ──

function StatCard({
  label, value, subtitle, icon: Icon, trend,
}: {
  label: string
  value: string
  subtitle?: string
  icon: React.ComponentType<{ className?: string }>
  trend?: 'up' | 'down' | 'neutral'
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-gray-200/60 dark:border-gray-700/60 bg-white dark:bg-gray-800/80 p-5 shadow-sm hover:shadow-md transition-all duration-200">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">{label}</p>
          <p className={cn(
            'text-2xl font-bold tracking-tight',
            trend === 'up' && 'text-emerald-600 dark:text-emerald-400',
            trend === 'down' && 'text-red-600 dark:text-red-400',
            !trend && 'text-gray-900 dark:text-white',
          )}>{value}</p>
          {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>}
        </div>
        <div className={cn(
          'rounded-xl p-2.5',
          trend === 'up' && 'bg-emerald-50 dark:bg-emerald-900/30',
          trend === 'down' && 'bg-red-50 dark:bg-red-900/30',
          !trend && 'bg-blue-50 dark:bg-blue-900/30',
        )}>
          <Icon className={cn(
            'h-5 w-5',
            trend === 'up' && 'text-emerald-600 dark:text-emerald-400',
            trend === 'down' && 'text-red-600 dark:text-red-400',
            !trend && 'text-blue-600 dark:text-blue-400',
          )} />
        </div>
      </div>
    </div>
  )
}

// ── Benchmark Bar ──

function BenchmarkBar({ name, value, fundReturn, color }: {
  name: string; value: number; fundReturn: number; color: string
}) {
  const maxVal = Math.max(value, fundReturn) * 1.2
  const barWidth = Math.max(0, (value / maxVal) * 100)
  const fundWidth = Math.max(0, (fundReturn / maxVal) * 100)
  const diff = fundReturn - value

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-700 dark:text-gray-300">{name}</span>
        <div className="flex items-center gap-3">
          <span className="text-gray-500 dark:text-gray-400">{fmtPct(value)}</span>
          <span className={cn(
            'text-xs font-semibold px-1.5 py-0.5 rounded-full',
            diff >= 0 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
          )}>
            {diff >= 0 ? '+' : ''}{diff.toFixed(2)}%
          </span>
        </div>
      </div>
      <div className="relative h-2.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        <div className="absolute inset-y-0 left-0 rounded-full opacity-40" style={{ width: `${barWidth}%`, backgroundColor: color }} />
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${fundWidth}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

// ── Section Header ──

function SectionHeader({ icon: Icon, title, subtitle }: {
  icon: React.ComponentType<{ className?: string }>; title: string; subtitle?: string
}) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="rounded-lg bg-blue-50 dark:bg-blue-900/30 p-2">
        <Icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
        {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
      </div>
    </div>
  )
}

// ── Loading Skeleton ──

function DashboardSkeleton() {
  return (
    <div className="space-y-8 animate-pulse" aria-label="Loading dashboard">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={`skel-stat-${i}`} className="h-28 rounded-2xl bg-gray-200 dark:bg-gray-700" />
        ))}
      </div>
      <div className="h-80 rounded-2xl bg-gray-200 dark:bg-gray-700" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-64 rounded-2xl bg-gray-200 dark:bg-gray-700" />
        <div className="h-64 rounded-2xl bg-gray-200 dark:bg-gray-700" />
      </div>
    </div>
  )
}

// ── Error Display ──

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6 text-center">
      <p className="text-red-800 dark:text-red-200 font-medium mb-2">Failed to load data</p>
      <p className="text-sm text-red-600 dark:text-red-300 mb-4">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
      )}
    </div>
  )
}

// ── Main Dashboard ──

export default function Home() {
  const [selectedCnpj, setSelectedCnpj] = useState<string | null>(null)

  const { data: funds = [], isLoading: fundsLoading, error: fundsError } = useQuery({
    queryKey: ['funds'],
    queryFn: apiClient.getFunds,
    staleTime: 1000 * 60 * 5,
  })

  const currentCnpj = useMemo(() => {
    if (selectedCnpj) return selectedCnpj
    if (funds.length > 0) return funds[0].cnpj
    return null
  }, [selectedCnpj, funds])

  const {
    data: perf,
    isLoading: perfLoading,
    error: perfError,
    refetch: refetchPerf,
  } = useQuery({
    queryKey: ['performance', currentCnpj],
    queryFn: () => apiClient.getFundPerformance(currentCnpj!),
    enabled: !!currentCnpj,
    staleTime: 1000 * 60 * 5,
  })

  const { data: dailyData = [] } = useQuery({
    queryKey: ['daily', currentCnpj],
    queryFn: () => apiClient.getFundDaily(currentCnpj!, 90),
    enabled: !!currentCnpj,
    staleTime: 1000 * 60 * 5,
  })

  const currentFund = funds.find((f: Fund) => f.cnpj === currentCnpj)
  const isLoading = fundsLoading || perfLoading
  const error = fundsError || perfError

  const navChartData = useMemo(() => {
    if (dailyData.length === 0) return []
    return dailyData.map((d) => ({
      date: fmtDate(d.date),
      nav: d.nav,
    }))
  }, [dailyData])

  const flowChartData = useMemo(() => {
    if (dailyData.length === 0) return []
    const monthly: Record<string, { deposits: number; withdrawals: number; label: string }> = {}
    for (const d of dailyData) {
      const key = d.date.slice(0, 7)
      if (!monthly[key]) {
        monthly[key] = {
          deposits: 0,
          withdrawals: 0,
          label: new Date(`${d.date}T12:00:00`).toLocaleDateString('pt-BR', { month: 'short' }),
        }
      }
      monthly[key].deposits += d.deposits
      monthly[key].withdrawals += d.withdrawals
    }
    return Object.values(monthly).map((m) => ({
      date: m.label,
      deposits: m.deposits / 1_000_000,
      withdrawals: -(m.withdrawals / 1_000_000),
    }))
  }, [dailyData])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-blue-50/30 dark:from-gray-950 dark:via-gray-900 dark:to-blue-950/20">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-gray-200/80 dark:border-gray-800/80 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">Market Analysis</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">Fund performance dashboard — real-time data</p>
            </div>
            <div className="flex items-center gap-3">
              <label htmlFor="fund-select" className="sr-only">Select Fund</label>
              <select
                id="fund-select"
                value={currentCnpj ?? ''}
                onChange={(e) => setSelectedCnpj(e.target.value)}
                disabled={fundsLoading}
                className="min-w-[280px] rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 text-sm font-medium text-gray-900 dark:text-white shadow-sm focus:ring-2 focus:ring-blue-500 focus:outline-none disabled:opacity-50"
              >
                <option value="">{fundsLoading ? 'Loading...' : 'Select a fund'}</option>
                {funds.map((fund: Fund) => (
                  <option key={fund.cnpj} value={fund.cnpj}>
                    {fund.short_name} — {fund.fund_type}
                  </option>
                ))}
              </select>
              {perf && (
                <button
                  type="button"
                  onClick={() => refetchPerf()}
                  className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2.5 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 shadow-sm transition-all"
                  aria-label="Refresh data"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <ErrorBanner
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetchPerf()}
          />
        )}

        {isLoading && <DashboardSkeleton />}

        {!isLoading && !perf && !error && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <BarChart3 className="h-16 w-16 text-gray-300 dark:text-gray-600 mb-4" />
            <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300">Select a fund to begin</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Choose a fund from the dropdown above</p>
          </div>
        )}

        {perf && currentFund && (
          <div className="space-y-8">
            {/* Fund Header */}
            <div className="rounded-2xl border border-gray-200/60 dark:border-gray-700/60 bg-white dark:bg-gray-800/80 p-6 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">{currentFund.name}</h2>
                    <span className={cn(
                      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
                      currentFund.status === 'active'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
                    )}>
                      {currentFund.status === 'active' ? 'Active' : currentFund.status}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500 dark:text-gray-400">
                    <span>CNPJ: {currentFund.cnpj}</span>
                    <span className="hidden sm:inline">&bull;</span>
                    <span>{currentFund.fund_type}</span>
                    <span className="hidden sm:inline">&bull;</span>
                    <span>{currentFund.manager}</span>
                    <span className="hidden sm:inline">&bull;</span>
                    <span>Benchmark: {currentFund.benchmark}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>{perf.period.start} — {perf.period.end} ({perf.period.days} days)</span>
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label="Period Return"
                value={fmtPct(perf.performance.return_pct)}
                subtitle={`NAV: ${fmtNum(perf.performance.nav_start, 6)} → ${fmtNum(perf.performance.nav_end, 6)}`}
                icon={perf.performance.return_pct >= 0 ? TrendingUp : TrendingDown}
                trend={perf.performance.return_pct >= 0 ? 'up' : 'down'}
              />
              <StatCard
                label="Volatility"
                value={`${fmtNum(perf.risk.volatility)}%`}
                subtitle={`Sharpe: ${fmtNum(perf.risk.sharpe_ratio)}`}
                icon={Activity}
              />
              <StatCard
                label="Shareholders"
                value={perf.market.shareholders.toLocaleString('pt-BR')}
                subtitle={`Trend 30d: ${perf.market.trend_30d}`}
                icon={Users}
                trend={perf.market.trend_30d === 'up' ? 'up' : perf.market.trend_30d === 'down' ? 'down' : 'neutral'}
              />
              <StatCard
                label="Equity (AUM)"
                value={fmtCompact(perf.market.equity_millions * 1_000_000)}
                subtitle={`Alpha: ${fmtPct(perf.efficiency.alpha)}`}
                icon={DollarSign}
              />
            </div>

            {/* NAV Chart */}
            {navChartData.length > 0 && (
              <div className="rounded-2xl border border-gray-200/60 dark:border-gray-700/60 bg-white dark:bg-gray-800/80 p-6 shadow-sm">
                <SectionHeader icon={TrendingUp} title="NAV Evolution" subtitle="Daily net asset value over the period" />
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={navChartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                      <defs>
                        <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
                      <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `R$ ${v.toFixed(3)}`} domain={['auto', 'auto']} />
                      <RechartsTooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '12px', padding: '12px', fontSize: '13px' }}
                        labelStyle={{ color: '#9ca3af', marginBottom: '4px' }}
                        itemStyle={{ color: '#fff' }}
                        formatter={(value) => [`R$ ${Number(value).toFixed(6)}`, 'NAV']}
                      />
                      <Area type="monotone" dataKey="nav" stroke="#3b82f6" strokeWidth={2.5} fill="url(#navGradient)" dot={false} activeDot={{ r: 5, strokeWidth: 2, fill: '#fff', stroke: '#3b82f6' }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Two columns: Risk + Benchmarks */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Risk & Efficiency */}
              <div className="rounded-2xl border border-gray-200/60 dark:border-gray-700/60 bg-white dark:bg-gray-800/80 p-6 shadow-sm">
                <SectionHeader icon={Shield} title="Risk & Efficiency" subtitle="Key risk-adjusted performance indicators" />
                <div className="space-y-4">
                  {[
                    { label: 'VaR 95%', value: fmtPct(perf.risk.var_95), desc: 'Maximum expected loss at 95% confidence' },
                    { label: 'Max Drawdown', value: fmtPct(perf.risk.max_drawdown), desc: 'Worst peak-to-trough decline' },
                    { label: 'Sharpe Ratio', value: fmtNum(perf.risk.sharpe_ratio), desc: 'Risk-adjusted return measure' },
                    { label: 'Alpha', value: fmtPct(perf.efficiency.alpha), desc: 'Excess return vs benchmark' },
                    { label: 'Beta', value: fmtNum(perf.efficiency.beta), desc: 'Market sensitivity coefficient' },
                    { label: 'Volatility', value: `${fmtNum(perf.risk.volatility)}%`, desc: 'Annualized price variability' },
                  ].map((metric) => (
                    <div key={metric.label} className="flex items-center justify-between py-2.5 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{metric.label}</p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">{metric.desc}</p>
                      </div>
                      <span className="text-sm font-bold text-gray-900 dark:text-white tabular-nums">{metric.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Benchmarks */}
              <div className="rounded-2xl border border-gray-200/60 dark:border-gray-700/60 bg-white dark:bg-gray-800/80 p-6 shadow-sm">
                <SectionHeader icon={Target} title="Benchmark Comparison" subtitle={`Fund return: ${fmtPct(perf.performance.return_pct)} in ${perf.period.days} days`} />
                <div className="space-y-5">
                  <BenchmarkBar name="CDI" value={perf.benchmarks.cdi.accumulated} fundReturn={perf.performance.return_pct} color="#3b82f6" />
                  <BenchmarkBar name="SELIC" value={perf.benchmarks.selic.accumulated} fundReturn={perf.performance.return_pct} color="#8b5cf6" />
                  <BenchmarkBar name="IPCA" value={perf.benchmarks.ipca.accumulated} fundReturn={perf.performance.return_pct} color="#f59e0b" />
                  <BenchmarkBar name="CDB (est.)" value={perf.benchmarks.cdb.estimated} fundReturn={perf.performance.return_pct} color="#10b981" />
                  <BenchmarkBar name="Poupanca (est.)" value={perf.benchmarks.poupanca.estimated} fundReturn={perf.performance.return_pct} color="#6b7280" />
                </div>
                <div className="mt-6 rounded-xl bg-gray-50 dark:bg-gray-900/50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">% CDI Captured</p>
                  <div className="text-3xl font-black text-blue-600 dark:text-blue-400">
                    {perf.benchmarks.cdi.accumulated > 0
                      ? `${((perf.performance.return_pct / perf.benchmarks.cdi.accumulated) * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {perf.performance.return_pct >= perf.benchmarks.cdi.accumulated ? 'Outperforming CDI' : 'Underperforming CDI'}
                  </p>
                </div>
              </div>
            </div>

            {/* Cash Flow */}
            {flowChartData.length > 0 && (
              <div className="rounded-2xl border border-gray-200/60 dark:border-gray-700/60 bg-white dark:bg-gray-800/80 p-6 shadow-sm">
                <SectionHeader icon={Zap} title="Monthly Capital Flow" subtitle="Deposits vs withdrawals in millions (R$)" />
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={flowChartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
                      <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}M`} />
                      <RechartsTooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '12px', padding: '12px', fontSize: '13px' }}
                        formatter={(value, name) => [
                          `R$ ${Math.abs(Number(value)).toFixed(1)}M`,
                          name === 'deposits' ? 'Deposits' : 'Withdrawals',
                        ]}
                      />
                      <Bar dataKey="deposits" fill="#10b981" radius={[6, 6, 0, 0]} />
                      <Bar dataKey="withdrawals" fill="#ef4444" radius={[0, 0, 6, 6]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Market Context Footer */}
            <div className="rounded-2xl border border-gray-200/60 dark:border-gray-700/60 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/20 p-6 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-4 flex-wrap">
                  <div className="flex items-center gap-2">
                    {perf.market.trend_30d === 'up'
                      ? <ArrowUpRight className="h-5 w-5 text-emerald-600" />
                      : <ArrowDownRight className="h-5 w-5 text-red-600" />}
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      30-day trend: <strong className={perf.market.trend_30d === 'up' ? 'text-emerald-600' : 'text-red-600'}>
                        {perf.market.trend_30d.toUpperCase()}
                      </strong>
                    </span>
                  </div>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {perf.market.shareholders.toLocaleString('pt-BR')} shareholders
                  </span>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    AUM: {fmtCompact(perf.market.equity_millions * 1_000_000)}
                  </span>
                </div>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  Updated: {new Date(perf.updated_at).toLocaleString('pt-BR')}
                </span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
