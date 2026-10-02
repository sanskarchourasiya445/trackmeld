'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { BenchmarkComparisonResult, BenchmarkComparisonRow } from '@/types/planning';
import { benchmarkSchedule } from '@/lib/api/client';
import { BarChart3, RefreshCw, Info } from 'lucide-react';

interface BenchmarkComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  scenarioId: string;
}

export const BenchmarkComparisonModal: React.FC<BenchmarkComparisonModalProps> = ({
  isOpen,
  onClose,
  scenarioId,
}) => {
  const [loading, setLoading] = useState(false);
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleManualRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await benchmarkSchedule(scenarioId, true, 5.0);
      setBenchmarkData(data);
    } catch (err: unknown) {
      console.error('Failed to run benchmark:', err);
      setError(err instanceof Error ? err.message : 'Benchmark calculation failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    if (isOpen && !benchmarkData) {
      benchmarkSchedule(scenarioId, true, 5.0)
        .then((data) => {
          if (!cancelled) setBenchmarkData(data);
        })
        .catch((err) => {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : 'Benchmark calculation failed');
          }
        });
    }
    return () => {
      cancelled = true;
    };
  }, [isOpen, scenarioId, benchmarkData]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="bg-[#141418] border border-[#29292F] text-[#F5F5F5] sm:max-w-3xl p-6 font-mono">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-[#4C87E7]/10 border border-[#4C87E7]/30 flex items-center justify-center">
                <BarChart3 className="w-4 h-4 text-[#4C87E7]" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-[#F5F5F5]">
                  Comparative Strategy Benchmark
                </DialogTitle>
                <DialogDescription className="text-xs text-[#A1A1AA]">
                  Side-by-side performance evaluation on identical operational snapshot
                </DialogDescription>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              disabled={loading}
              className="border-[#29292F] text-xs text-[#A1A1AA] hover:text-white"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Re-run Benchmark
            </Button>
          </div>
        </DialogHeader>

        {/* Informational Callout */}
        <div className="bg-[#0E0E12] border border-[#202024] rounded p-3 text-xs text-[#A1A1AA] space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#F5F5F5]">
            <Info className="w-3.5 h-3.5 text-[#4C87E7]" />
            <span>Factual Algorithm Comparison (Zero Subjective Bias)</span>
          </div>
          <p className="text-[11px] leading-relaxed text-[#71717A]">
            Metrics are evaluated deterministically on the exact same corridor snapshot ({scenarioId})
            under identical safety clearances, headway rules, and work windows. No heuristics or models
            are labeled &apos;winner&apos; or &apos;best&apos;—values reflect empirical operational trade-offs.
          </p>
        </div>

        {/* Table Content */}
        {loading && !benchmarkData ? (
          <div className="py-12 flex flex-col items-center justify-center text-[#71717A] text-xs">
            <RefreshCw className="w-6 h-6 animate-spin mb-2 text-[#4C87E7]" />
            <span>Executing benchmark across FCFS, Priority-Greedy, and CP-SAT engines...</span>
          </div>
        ) : error ? (
          <div className="py-8 text-center text-xs text-rose-400">
            Error loading benchmark results: {error}
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-[#202024] bg-[#0E0E12]">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#18181C] border-b border-[#202024] text-[10px] uppercase text-[#71717A]">
                  <th className="py-2.5 px-3 font-semibold">Evaluation Metric</th>
                  <th className="py-2.5 px-3 font-semibold text-right">FCFS</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Priority-Greedy</th>
                  <th className="py-2.5 px-3 font-semibold text-right text-[#4C87E7]">CP-SAT (Global)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#202024]/60 text-[11px]">
                {benchmarkData?.comparison_table.map((row: BenchmarkComparisonRow, idx: number) => {
                  const isHighlight =
                    row.metric.includes('Completion Rate') ||
                    row.metric.includes('Captured Priority') ||
                    row.metric.includes('Latency');

                  return (
                    <tr
                      key={idx}
                      className={isHighlight ? 'bg-[#141418]/60 font-semibold' : 'hover:bg-[#141418]/30'}
                    >
                      <td className="py-2 px-3 text-[#D4D4D8]">{row.metric}</td>
                      <td className="py-2 px-3 text-right text-[#A1A1AA]">
                        {String(row['FCFS'] ?? '—')}
                      </td>
                      <td className="py-2 px-3 text-right text-[#A1A1AA]">
                        {String(row['Priority-Greedy'] ?? '—')}
                      </td>
                      <td className="py-2 px-3 text-right text-[#F5F5F5] font-bold">
                        {String(row['CP-SAT'] ?? '—')}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <DialogFooter className="flex items-center justify-between sm:justify-between pt-2 border-t border-[#202024]">
          <span className="text-[10px] text-[#71717A]">
            Snapshot: {benchmarkData?.snapshot_id ?? 'SNAP-DEMO'}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            className="border-[#29292F] text-xs text-[#A1A1AA]"
          >
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
