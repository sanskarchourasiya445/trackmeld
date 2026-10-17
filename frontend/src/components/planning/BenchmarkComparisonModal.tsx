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
import { BarChart3, RefreshCw, Info, GitCompare } from 'lucide-react';

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
      <DialogContent className="bg-[#0B101C] border border-[#1E2D4A] text-[#F8FAFC] sm:max-w-3xl p-6 font-sans">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8]">
                <GitCompare className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-[#F8FAFC]">
                  Plan Benchmark Comparison
                </DialogTitle>
                <DialogDescription className="text-xs text-[#94A3B8]">
                  Comparative dispatch evaluations on identical operational snapshot
                </DialogDescription>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              disabled={loading}
              className="border-[#2D436D] text-xs text-[#CBD5E1] hover:text-white h-8"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Re-run Benchmark
            </Button>
          </div>
        </DialogHeader>

        {/* Informational Callout */}
        <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3.5 text-xs text-[#94A3B8] space-y-1 font-sans">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#F8FAFC]">
            <Info className="w-4 h-4 text-[#38BDF8]" />
            <span>Factual Algorithm Comparison (Zero Subjective Bias)</span>
          </div>
          <p className="text-[11px] leading-relaxed text-[#94A3B8]">
            Metrics are evaluated deterministically on the exact same corridor snapshot ({scenarioId})
            under identical safety clearances, headway rules, and work windows. Values reflect empirical operational trade-offs.
          </p>
        </div>

        {/* Table Content */}
        {loading && !benchmarkData ? (
          <div className="py-12 flex flex-col items-center justify-center text-[#94A3B8] text-xs">
            <RefreshCw className="w-6 h-6 animate-spin mb-2 text-[#38BDF8]" />
            <span>Executing benchmark across FCFS, Priority-Greedy, and CP-SAT engines...</span>
          </div>
        ) : error ? (
          <div className="py-8 text-center text-xs text-rose-400">
            Error loading benchmark results: {error}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-[#1E2D4A] bg-[#0F172A]">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#141F36] border-b border-[#1E2D4A] text-[10px] font-mono uppercase text-[#64748B]">
                  <th className="py-3 px-3.5 font-bold">Evaluation Metric</th>
                  <th className="py-3 px-3.5 font-semibold text-right">FCFS</th>
                  <th className="py-3 px-3.5 font-semibold text-right">Priority-Greedy</th>
                  <th className="py-3 px-3.5 font-bold text-right text-[#38BDF8]">CP-SAT (Global)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2D4A]/60 font-mono text-[11px]">
                {benchmarkData?.comparison_table.map((row: BenchmarkComparisonRow, idx: number) => {
                  const isHighlight =
                    row.metric.includes('Completion Rate') ||
                    row.metric.includes('Captured Priority') ||
                    row.metric.includes('Latency');

                  return (
                    <tr
                      key={idx}
                      className={isHighlight ? 'bg-[#141F36]/60 font-semibold' : 'hover:bg-[#141F36]/30'}
                    >
                      <td className="py-2.5 px-3.5 text-[#F8FAFC] font-sans">{row.metric}</td>
                      <td className="py-2.5 px-3.5 text-right text-[#94A3B8]">
                        {String(row['FCFS'] ?? '—')}
                      </td>
                      <td className="py-2.5 px-3.5 text-right text-[#94A3B8]">
                        {String(row['Priority-Greedy'] ?? '—')}
                      </td>
                      <td className="py-2.5 px-3.5 text-right text-emerald-400 font-bold">
                        {String(row['CP-SAT'] ?? '—')}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <DialogFooter className="flex items-center justify-between sm:justify-between pt-3 border-t border-[#1E2D4A]">
          <span className="text-[11px] font-mono text-[#64748B]">
            Snapshot: {benchmarkData?.snapshot_id ?? 'SNAP-DEMO'}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            className="border-[#2D436D] text-xs text-[#CBD5E1]"
          >
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
