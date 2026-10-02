'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/shell/AppShell';
import { MetricCard } from '@/components/common/MetricCard';
import {
  getScenarioBundle,
  DEMO_SCENARIO,
  DEMO_CORRIDOR,
  DEMO_TASKS,
  DEMO_SCHEDULE_RESULT,
} from '@/lib/api/client';
import {
  ArrowRight,
  RefreshCw,
  Clock,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  Cpu,
  Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RailwayFallback2D } from '@/components/railway/RailwayFallback2D';

export default function OverviewPage() {
  const [tasksCount, setTasksCount] = useState(82);
  const [scheduledCount, setScheduledCount] = useState(67);
  const [unplacedCount, setUnplacedCount] = useState(15);
  const activeResourcesCount = 21;
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState('30 Mar 2026, 14:32');

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0007');
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-12');

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const bundle = await getScenarioBundle('SCN-DEMO-001');
      if (bundle.tasks) {
        setTasksCount(bundle.tasks.length);
        const scheduled = bundle.tasks.filter((t) => t.status === 'SCHEDULED').length;
        setScheduledCount(scheduled || 67);
        setUnplacedCount(bundle.tasks.length - scheduled || 15);
      }
      setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', Today');
    } catch (err) {
      console.warn('Overview refresh error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      activeScenarioId={DEMO_SCENARIO.scenario_id}
      tasksCount={tasksCount}
      trainsCount={50}
      userRole="Operations Officer"
      userName="Operator"
      onRefresh={handleRefresh}
    >
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-4 max-w-[1600px] w-full mx-auto font-sans">
        {/* 1. Header & Situation Briefing */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#1E2D4A]">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#F8FAFC]">
              Operations Overview
            </h1>
            <p className="text-xs text-[#94A3B8] mt-0.5">
              Network performance, planning status and key indicators
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#64748B]">
            <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#94A3B8]">
              <Clock className="w-3.5 h-3.5 text-[#3B82F6]" />
              <span>Last updated: {lastUpdated}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading}
              className="border-[#1E2D4A] hover:bg-[#141F36] text-[#F8FAFC] text-xs h-7 px-2.5 font-sans gap-1.5"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* 2. Compact 4 KPI Cards Strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <MetricCard
            label="Total Tasks"
            value={tasksCount}
            delta={{ value: '+12% vs last period', isPositive: true }}
            icon={<Activity className="w-3.5 h-3.5 text-[#3B82F6]" />}
          />
          <MetricCard
            label="Scheduled Tasks"
            value={scheduledCount}
            subtext="81.7% completion"
            icon={<CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
          />
          <MetricCard
            label="Unplaced Tasks"
            value={unplacedCount}
            subtext="18.3% pending"
            icon={<AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
          />
          <MetricCard
            label="Active Resources"
            value={activeResourcesCount}
            subtext="of 24 available"
            icon={<Cpu className="w-3.5 h-3.5 text-sky-400" />}
          />
        </div>

        {/* 3. Main Split View: Corridor Map (Left) + Analytics & Feed (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left: Network Corridor Map (Col 7 or 8) */}
          <div className="lg:col-span-8 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-4 flex flex-col justify-between shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A] mb-3">
              <div>
                <h2 className="text-sm font-bold text-[#F8FAFC]">
                  Network Corridor View
                </h2>
                <span className="text-[11px] text-[#94A3B8]">
                  Northern Corridor ({DEMO_CORRIDOR.total_length_km} km) • Trunk Route
                </span>
              </div>
              <Link href="/planning">
                <Button size="sm" variant="ghost" className="text-xs text-[#3B82F6] hover:text-white hover:bg-[#141F36] h-7 px-2 font-medium">
                  Open Interactive Workstation
                  <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </Link>
            </div>

            {/* Schematic Corridor Map */}
            <div className="h-[360px] w-full rounded-md border border-[#1E2D4A] bg-[#080C14] overflow-hidden relative">
              <RailwayFallback2D
                corridor={DEMO_CORRIDOR}
                tasks={DEMO_TASKS}
                scheduleResult={DEMO_SCHEDULE_RESULT}
                selectedTaskId={selectedTaskId}
                selectedSectionCode={selectedSectionCode}
                onSelectTask={setSelectedTaskId}
                onSelectSection={setSelectedSectionCode}
              />
            </div>

            {/* Map Legend */}
            <div className="mt-3 pt-3 border-t border-[#1E2D4A] flex flex-wrap items-center justify-between gap-3 text-[11px] text-[#94A3B8]">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-1 bg-[#64748B] rounded"></span>
                  Track Sections
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-1.5 bg-[#F59E0B] rounded"></span>
                  Maintenance Task
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-1 bg-[#3B82F6] rounded"></span>
                  Train Pass
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-1.5 bg-rose-500 rounded"></span>
                  Block Section
                </span>
              </div>

              <div className="font-mono text-[10px] text-[#64748B]">
                Delhi (km 0) → Kanpur (km 440)
              </div>
            </div>
          </div>

          {/* Right: Scheduler Comparison + Recent Activity Feed (Col 4) */}
          <div className="lg:col-span-4 space-y-4">
            {/* Scheduler Comparison Card */}
            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-4 shadow-sm">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#1E2D4A] mb-3">
                <h3 className="text-xs font-bold text-[#F8FAFC]">
                  Scheduler Comparison
                </h3>
                <div className="flex items-center gap-3 text-[10px] font-mono">
                  <span className="flex items-center gap-1 text-[#3B82F6]">
                    <span className="w-2 h-2 rounded bg-[#3B82F6]"></span>
                    CP-SAT (Optimal)
                  </span>
                  <span className="flex items-center gap-1 text-[#10B981]">
                    <span className="w-2 h-2 rounded bg-[#10B981]"></span>
                    Greedy (Baseline)
                  </span>
                </div>
              </div>

              {/* Bar Comparison Metrics */}
              <div className="space-y-3 text-xs">
                <div>
                  <div className="flex items-center justify-between text-[11px] mb-1">
                    <span className="text-[#94A3B8]">Tasks Scheduled</span>
                    <span className="font-mono font-bold text-[#F8FAFC]">67 vs 61</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 h-2">
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#3B82F6] h-full rounded-full" style={{ width: '81.7%' }}></div>
                    </div>
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#10B981] h-full rounded-full" style={{ width: '74.3%' }}></div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-[11px] mb-1">
                    <span className="text-[#94A3B8]">Total Duration (%)</span>
                    <span className="font-mono font-bold text-[#F8FAFC]">74.8% vs 81.2%</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 h-2">
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#3B82F6] h-full rounded-full" style={{ width: '74.8%' }}></div>
                    </div>
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#10B981] h-full rounded-full" style={{ width: '81.2%' }}></div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-[11px] mb-1">
                    <span className="text-[#94A3B8]">Conflicts Encountered</span>
                    <span className="font-mono font-bold text-[#F8FAFC]">0 vs 3</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 h-2">
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#3B82F6] h-full rounded-full" style={{ width: '0%' }}></div>
                    </div>
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#10B981] h-full rounded-full" style={{ width: '25%' }}></div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-[11px] mb-1">
                    <span className="text-[#94A3B8]">Feasibility Score</span>
                    <span className="font-mono font-bold text-emerald-400">98.6% vs 92.4%</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 h-2">
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#3B82F6] h-full rounded-full" style={{ width: '98.6%' }}></div>
                    </div>
                    <div className="bg-[#141F36] rounded-full overflow-hidden">
                      <div className="bg-[#10B981] h-full rounded-full" style={{ width: '92.4%' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity Card */}
            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-4 shadow-sm">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#1E2D4A] mb-3">
                <h3 className="text-xs font-bold text-[#F8FAFC]">
                  Recent Activity
                </h3>
                <Link href="/audit" className="text-[11px] text-[#3B82F6] hover:underline font-medium">
                  View Full Audit
                </Link>
              </div>

              <div className="space-y-3">
                <div className="flex items-start gap-2.5 text-xs">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                    <CheckCircle className="w-3 h-3" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[#F8FAFC] font-medium leading-tight">
                      Plan version v1.0.3 approved by ops_officer
                    </div>
                    <div className="text-[10px] text-[#64748B] font-mono mt-0.5">
                      1h ago • Formal sign-off
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 text-xs">
                  <div className="w-5 h-5 rounded-full bg-[#2563EB]/10 border border-[#2563EB]/30 flex items-center justify-center text-[#3B82F6] shrink-0 mt-0.5">
                    <Cpu className="w-3 h-3" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[#F8FAFC] font-medium leading-tight">
                      Planning run SCN-DEMO-001 completed
                    </div>
                    <div className="text-[10px] text-[#64748B] font-mono mt-0.5">
                      2h ago • CP-SAT solver (optimal)
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 text-xs">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                    <ShieldCheck className="w-3 h-3" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[#F8FAFC] font-medium leading-tight">
                      Validation passed (0 errors, 2 warnings)
                    </div>
                    <div className="text-[10px] text-[#64748B] font-mono mt-0.5">
                      3h ago • Independent Validator
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 text-xs">
                  <div className="w-5 h-5 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
                    <AlertTriangle className="w-3 h-3" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[#F8FAFC] font-medium leading-tight">
                      Task TSK-0007 remains unplaced
                    </div>
                    <div className="text-[10px] text-[#64748B] font-mono mt-0.5">
                      5h ago • Section SEC-12 traffic conflict
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
