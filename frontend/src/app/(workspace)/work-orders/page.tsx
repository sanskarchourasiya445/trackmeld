'use client';

import React, { useState } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { EntityInspector } from '@/components/planning/EntityInspector';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';
import { DigitalTwinInspectionModal } from '@/components/digital-twin/DigitalTwinInspectionModal';
import { DEMO_TASKS, DEMO_SCHEDULE_RESULT } from '@/lib/api/client';
import { MaintenanceTask, formatTrackSpatial } from '@/types/railway';
import {
  ClipboardList,
  Search,
  Filter,
  CheckCircle,
  AlertTriangle,
  Clock,
  Wrench,
  ShieldCheck,
  Eye,
  PanelRight,
  ArrowUpDown,
  Download,
  Plus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export const EXTENDED_WORK_ORDERS: MaintenanceTask[] = [
  ...DEMO_TASKS,
  {
    task_id: 'TSK-0002',
    task_code: 'WO-1848',
    title: 'Ballast Cleaning Machine (BCM) Sifting & Deep Screening',
    work_type: 'BALLAST_CLEANING',
    department: 'ENGINEERING',
    section_code: 'SEC-GZB-ALJN',
    section_id: 'SEC-GZB-ALJN',
    track_id: 'GZB-ALJN-UP',
    from_km: 64.2,
    to_km: 68.5,
    required_duration_minutes: 240,
    window_start: '2026-10-18T01:00:00Z',
    window_end: '2026-10-18T06:00:00Z',
    urgency: 'HIGH',
    priority: 'HIGH',
    status: 'SCHEDULED',
    crew_id: 'CREW-ENG-BCM-01',
    machinery_required: ['BCM-09', 'DGS-Track-Stabilizer'],
    requires_traffic_block: true,
  },
  {
    task_id: 'TSK-0003',
    task_code: 'WO-1849',
    title: 'Catenary Contact Wire Tensioning & Insulator Replacement',
    work_type: 'OHE_MAINTENANCE',
    department: 'ELECTRICAL_TRD',
    section_code: 'SEC-TDL-ETW',
    section_id: 'SEC-TDL-ETW',
    track_id: 'TDL-ETW-DN',
    from_km: 235.0,
    to_km: 238.4,
    required_duration_minutes: 150,
    window_start: '2026-10-18T02:30:00Z',
    window_end: '2026-10-18T06:00:00Z',
    urgency: 'ROUTINE',
    priority: 'MEDIUM',
    status: 'SCHEDULED',
    crew_id: 'CREW-TRD-OHE-G02',
    machinery_required: ['Tower-Wagon-04'],
    requires_traffic_block: true,
    requires_ohe_isolation: true,
  },
  {
    task_id: 'TSK-0004',
    task_code: 'WO-1850',
    title: 'Point Machine Electrical Contacts & Throw Calibration',
    work_type: 'SIGNAL_INTERLOCKING',
    department: 'SIGNAL_AND_TELECOM',
    section_code: 'SEC-NDLS-GZB',
    section_id: 'SEC-NDLS-GZB',
    track_id: 'NDLS-YARD-SW4',
    from_km: 3.1,
    to_km: 3.2,
    required_duration_minutes: 90,
    window_start: '2026-10-18T03:00:00Z',
    window_end: '2026-10-18T05:30:00Z',
    urgency: 'CRITICAL',
    priority: 'CRITICAL',
    status: 'SCHEDULED',
    crew_id: 'CREW-ST-SIG-03',
    machinery_required: ['Point-Test-Kit'],
    requires_traffic_block: false,
  },
  {
    task_id: 'TSK-0005',
    task_code: 'WO-1851',
    title: 'Ultrasonic Flaw Detection (USFD) Rail Testing - UP Main',
    work_type: 'NON_DESTRUCTIVE_TESTING',
    department: 'ENGINEERING',
    section_code: 'SEC-ALJN-TDL',
    section_id: 'SEC-ALJN-TDL',
    track_id: 'ALJN-TDL-UP',
    from_km: 142.0,
    to_km: 155.0,
    required_duration_minutes: 180,
    window_start: '2026-10-18T07:00:00Z',
    window_end: '2026-10-18T11:00:00Z',
    urgency: 'HIGH',
    priority: 'HIGH',
    status: 'SCHEDULED',
    crew_id: 'CREW-USFD-G01',
    machinery_required: ['SRT-Double-Rail-Flaw-Detector'],
    requires_traffic_block: false,
  },
];

export default function WorkOrdersPage() {
  const [tasks] = useState<MaintenanceTask[]>(EXTENDED_WORK_ORDERS);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0001');
  const [searchQuery, setSearchQuery] = useState('');
  const [deptFilter, setDeptFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isDigitalTwinOpen, setIsDigitalTwinOpen] = useState(false);
  const [digitalTwinSection, setDigitalTwinSection] = useState('SEC-12');

  const selectedTask = tasks.find((t) => t.task_id === selectedTaskId) || tasks[0];
  const selectedScheduled = DEMO_SCHEDULE_RESULT.scheduled_tasks.find((st) => st.task_id === selectedTaskId);

  // Filtered Tasks
  const filteredTasks = tasks.filter((t) => {
    const matchesSearch =
      t.task_code?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.task_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.section_code?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDept = deptFilter === 'ALL' || t.department === deptFilter;
    const matchesStatus =
      statusFilter === 'ALL' ||
      (statusFilter === 'SCHEDULED' && t.task_id !== 'TSK-0007') ||
      (statusFilter === 'UNSCHEDULED' && t.task_id === 'TSK-0007');
    return matchesSearch && matchesDept && matchesStatus;
  });

  const scheduledCount = tasks.filter((t) => t.task_id !== 'TSK-0007').length;
  const unplacedCount = tasks.filter((t) => t.task_id === 'TSK-0007').length;

  const handleOpenDigitalTwin = (secCode: string) => {
    setDigitalTwinSection(secCode);
    setIsDigitalTwinOpen(true);
  };

  const handleRowClick = (taskId: string) => {
    setSelectedTaskId(taskId);
    setIsInspectorOpen(true);
  };

  return (
    <AppShell
      activeScenarioId="SCN-DEMO-001"
      scenarioName="Northern Trunk Corridor (NDLS - CNB)"
      planningHorizon="Maintenance Work Orders: 24h Window"
      tasksCount={tasks.length}
      trainsCount={50}
    >
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-2 sm:p-2.5 lg:p-3 gap-2 bg-[#04070D] font-sans max-w-[1920px] w-full mx-auto">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 bg-[#0B101C] border border-[#1E2D4A] rounded-lg px-3.5 py-2 shrink-0 shadow-sm">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8]">
                <ClipboardList className="w-4 h-4" />
              </div>
              <div>
                <h1 className="text-base font-bold text-[#F8FAFC]">Maintenance Work Orders & Requisitions</h1>
                <p className="text-[11px] text-[#94A3B8]">
                  Permanent Way (P-Way), S&T point machines, and 25 kV AC Traction electrical possession requests
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleOpenDigitalTwin(selectedTask?.section_code || 'SEC-12')}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#38BDF8] text-xs font-semibold h-7.5 px-2.5 cursor-pointer"
            >
              <Eye className="w-3.5 h-3.5 mr-1" />
              <span>3D Twin</span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsInspectorOpen((prev) => !prev)}
              className={`border-[#2D436D] text-xs font-semibold h-7.5 px-2.5 transition-colors cursor-pointer ${
                isInspectorOpen ? 'bg-[#141F36] text-white border-[#2563EB]' : 'text-[#CBD5E1] hover:text-white'
              }`}
            >
              <PanelRight className="w-3.5 h-3.5 mr-1 text-[#38BDF8]" />
              <span>{isInspectorOpen ? 'Close Drawer' : 'Inspect Selected'}</span>
            </Button>
          </div>
        </div>

        {/* Operational Statistics Row (Compact Operational KPI Strip) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 shrink-0">
          <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-lg px-3 py-1.5 flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#64748B] uppercase font-bold tracking-wider">
              Requisitions
            </span>
            <div className="flex items-baseline gap-1.5 font-mono">
              <span className="text-sm font-bold text-[#F8FAFC]">{tasks.length}</span>
              <span className="text-[10px] text-[#64748B]">Orders</span>
            </div>
          </div>
          <div className="bg-[#0B101C] border border-emerald-500/30 rounded-lg px-3 py-1.5 flex items-center justify-between">
            <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold tracking-wider">
              Certified
            </span>
            <div className="flex items-baseline gap-1.5 font-mono">
              <span className="text-sm font-bold text-emerald-400">{scheduledCount}</span>
              <span className="text-[10px] text-emerald-500/70">13/13 Pass</span>
            </div>
          </div>
          <div className="bg-[#0B101C] border border-rose-500/30 rounded-lg px-3 py-1.5 flex items-center justify-between">
            <span className="text-[10px] font-mono text-rose-400 uppercase font-bold tracking-wider">
              Unplaced
            </span>
            <div className="flex items-baseline gap-1.5 font-mono">
              <span className="text-sm font-bold text-rose-400">{unplacedCount}</span>
              <span className="text-[10px] text-rose-500/70">Headway</span>
            </div>
          </div>
          <div className="bg-[#0B101C] border border-[#2563EB]/30 rounded-lg px-3 py-1.5 flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#38BDF8] uppercase font-bold tracking-wider">
              Possessions
            </span>
            <div className="flex items-baseline gap-1.5 font-mono">
              <span className="text-sm font-bold text-[#38BDF8]">8 Blocks</span>
              <span className="text-[10px] text-[#38BDF8]/70">50 Trains</span>
            </div>
          </div>
        </div>

        {/* Filters and Search Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 bg-[#0B101C] border border-[#1E2D4A] rounded-lg px-3 py-1.5 shrink-0 text-xs">
          <div className="flex items-center gap-2 flex-1 max-w-md bg-[#0F172A] border border-[#1E2D4A] rounded-md px-2.5 py-1">
            <Search className="w-3.5 h-3.5 text-[#64748B] shrink-0" />
            <input
              type="text"
              placeholder="Search by ID, asset, task code, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent text-white placeholder-[#64748B] outline-none text-xs w-full font-mono"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Department Filter */}
            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              aria-label="Filter by department"
              className="bg-[#0F172A] border border-[#1E2D4A] text-[#CBD5E1] rounded-md px-2.5 py-1 text-xs outline-none cursor-pointer h-7"
            >
              <option value="ALL">All Departments</option>
              <option value="ENGINEERING">Civil Engineering (P-Way)</option>
              <option value="ELECTRICAL_TRD">Electrical (Traction OHE)</option>
              <option value="SIGNAL_AND_TELECOM">Signalling & Telecom (S&T)</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by schedule status"
              className="bg-[#0F172A] border border-[#1E2D4A] text-[#CBD5E1] rounded-md px-2.5 py-1 text-xs outline-none cursor-pointer h-7"
            >
              <option value="ALL">All Statuses</option>
              <option value="SCHEDULED">Scheduled (Certified)</option>
              <option value="UNSCHEDULED">Unplaced / Conflicts</option>
            </select>

            <span className="text-[11px] font-mono text-[#64748B] px-1">
              Showing {filteredTasks.length} of {tasks.length} orders
            </span>
          </div>
        </div>

        {/* Spacious Full-Width Table Workspace & Responsive Mobile Cards */}
        <div className="flex-1 min-h-0 bg-[#0B101C] border border-[#1E2D4A] rounded-lg overflow-hidden flex flex-col shadow-sm">
          {/* 1. Desktop & Tablet Responsive Table View (hidden on mobile < md) */}
          <div className="hidden md:flex flex-1 overflow-auto">
            {filteredTasks.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center gap-2.5">
                <div className="w-10 h-10 rounded-full bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#64748B]">
                  <Search className="w-5 h-5" />
                </div>
                <div className="font-semibold text-sm text-[#F8FAFC]">No work orders match filter criteria</div>
                <p className="text-xs text-[#64748B] max-w-sm">
                  Try adjusting the search query, department selection, or schedule status.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSearchQuery('');
                    setDeptFilter('ALL');
                    setStatusFilter('ALL');
                  }}
                  className="border-[#2D436D] text-xs text-[#38BDF8] hover:bg-[#141F36] h-7 mt-1"
                >
                  Reset Filters
                </Button>
              </div>
            ) : (
              <table className="w-full min-w-[900px] text-xs text-left border-collapse font-sans">
                <thead className="bg-[#0F172A] text-[#94A3B8] font-sans font-semibold uppercase text-[10px] sticky top-0 border-b border-[#1E2D4A] z-10 tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3 min-w-[95px]">ID / Code</th>
                    <th className="py-2.5 px-3 min-w-[240px]">Work Title & Type</th>
                    <th className="py-2.5 px-3 min-w-[130px]">Asset / Section</th>
                    <th className="py-2.5 px-3 min-w-[110px]">Department</th>
                    <th className="py-2.5 px-3 min-w-[85px]">Duration</th>
                    <th className="py-2.5 px-3 min-w-[90px]">Priority</th>
                    <th className="py-2.5 px-3 min-w-[120px] hidden xl:table-cell">Crew & Machinery</th>
                    <th className="py-2.5 px-3 min-w-[115px]">Schedule Status</th>
                    <th className="py-2.5 px-3 min-w-[95px] text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1E2D4A]/50">
                  {filteredTasks.map((t) => {
                    const isSelected = selectedTaskId === t.task_id;
                    const isUnplaced = t.task_id === 'TSK-0007';

                    return (
                      <tr
                        key={t.task_id}
                        tabIndex={0}
                        role="row"
                        aria-selected={isSelected}
                        onClick={() => handleRowClick(t.task_id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleRowClick(t.task_id);
                          }
                        }}
                        className={`transition-colors cursor-pointer outline-none border-b border-[#1E2D4A]/40 ${
                          isSelected
                            ? 'bg-[#13233F] text-white border-l-4 border-l-[#38BDF8] ring-1 ring-inset ring-[#2563EB]/40'
                            : 'hover:bg-[#141F36]/80 border-l-4 border-l-transparent text-[#CBD5E1]'
                        }`}
                      >
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span className="font-mono font-bold text-[#38BDF8] text-xs block">
                            {t.task_code || t.task_id}
                          </span>
                          <span className="text-[10px] text-[#64748B] font-mono block mt-0.5">
                            {t.task_id}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 min-w-[280px] max-w-[420px]">
                          <div className="font-semibold text-sm text-[#F8FAFC] leading-snug break-words">
                            {t.title}
                          </div>
                          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                            <span className="text-[10px] text-[#93C5FD] font-mono bg-[#141F36] px-1.5 py-0.5 rounded border border-[#2D436D]">
                              {t.work_type}
                            </span>
                            {t.requires_traffic_block && (
                              <span className="text-[10px] text-amber-400 font-mono bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-500/30">
                                BLOCK REQ
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-mono whitespace-nowrap">
                          <span className="font-semibold block text-[#F8FAFC]">
                            {t.section_code || t.section_id}
                          </span>
                          <span className="text-[10px] text-[#38BDF8] block mt-0.5">
                            {formatTrackSpatial(t)}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-[#CBD5E1] font-sans text-xs whitespace-nowrap">
                          {t.department?.replace(/_/g, ' ')}
                        </td>
                        <td className="py-3.5 px-4 font-mono whitespace-nowrap">
                          <span className="text-white font-medium">
                            {Math.floor((t.required_duration_minutes || 180) / 60)}h{' '}
                            {((t.required_duration_minutes || 180) % 60) > 0 ? `${(t.required_duration_minutes || 180) % 60}m` : ''}
                          </span>
                          <span className="text-[10px] text-[#64748B] block mt-0.5">
                            ({t.required_duration_minutes || 180} min)
                          </span>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            t.priority === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                              : t.priority === 'HIGH'
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                              : 'bg-blue-500/15 text-[#93C5FD] border-blue-500/30'
                          }`}>
                            {t.priority || 'ROUTINE'}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-[11px] max-w-[180px]">
                          <div className="font-medium text-[#F8FAFC] truncate">{t.crew_id || 'Gang A (6 Crew)'}</div>
                          <div className="text-[10px] text-[#94A3B8] truncate mt-0.5" title={t.machinery_required?.join(', ')}>
                            {t.machinery_required?.join(', ') || 'Track Machine'}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2.5 py-0.5 rounded border ${
                            isUnplaced
                              ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                              : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${isUnplaced ? 'bg-rose-400' : 'bg-emerald-400'}`} />
                            {isUnplaced ? 'UNPLACED' : 'SCHEDULED'}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRowClick(t.task_id);
                            }}
                            className="text-xs text-[#38BDF8] border-[#2D436D] hover:bg-[#141F36] hover:text-white mr-1.5 h-7.5 px-2.5"
                          >
                            Inspect
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenDigitalTwin(t.section_code || 'SEC-12');
                            }}
                            className="text-xs text-[#94A3B8] hover:text-white h-7.5 px-2"
                          >
                            3D Twin
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* 2. Mobile Responsive Compact Cards View (visible only on mobile < md) */}
          <div className="md:hidden flex-1 overflow-y-auto p-3 space-y-3">
            {filteredTasks.length === 0 ? (
              <div className="text-center py-10 text-xs text-[#94A3B8] flex flex-col items-center gap-2">
                <Search className="w-5 h-5 text-[#64748B]" />
                <span>No matching work orders found</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSearchQuery('');
                    setDeptFilter('ALL');
                    setStatusFilter('ALL');
                  }}
                  className="border-[#2D436D] text-xs text-[#38BDF8] hover:bg-[#141F36] h-7 px-2 mt-1"
                >
                  Reset Filters
                </Button>
              </div>
            ) : (
              filteredTasks.map((t) => {
                const isSelected = selectedTaskId === t.task_id;
                const isUnplaced = t.task_id === 'TSK-0007';

                return (
                  <div
                    key={t.task_id}
                    onClick={() => handleRowClick(t.task_id)}
                    tabIndex={0}
                    role="button"
                    aria-selected={isSelected}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleRowClick(t.task_id);
                      }
                    }}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-2.5 ${
                      isSelected
                        ? 'bg-[#13233F] border-[#38BDF8] shadow-md ring-1 ring-[#38BDF8]/40'
                        : 'bg-[#0E1526] border-[#1E2D4A] hover:bg-[#141F36]'
                    }`}
                  >
                    {/* Card Top: Code + Badges */}
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <span className="font-mono font-bold text-[#38BDF8] text-sm block">
                          {t.task_code || t.task_id}
                        </span>
                        <span className="text-[10px] font-mono text-[#64748B]">
                          {t.task_id} • {t.section_code || t.section_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 flex-wrap justify-end">
                        <span className={`text-[9.5px] font-mono font-bold px-2 py-0.5 rounded border ${
                          t.priority === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                            : t.priority === 'HIGH'
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                            : 'bg-blue-500/15 text-[#93C5FD] border-blue-500/30'
                        }`}>
                          {t.priority || 'ROUTINE'}
                        </span>
                        <span className={`text-[9.5px] font-mono font-bold px-2 py-0.5 rounded border ${
                          isUnplaced
                            ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                            : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                        }`}>
                          {isUnplaced ? 'UNPLACED' : 'SCHEDULED'}
                        </span>
                      </div>
                    </div>

                    {/* Card Title */}
                    <div className="font-semibold text-sm text-[#F8FAFC] leading-snug">
                      {t.title}
                    </div>

                    {/* Card Details Grid */}
                    <div className="grid grid-cols-2 gap-2 text-[11px] pt-1.5 border-t border-[#1E2D4A]/60">
                      <div>
                        <span className="text-[#64748B] text-[10px] block">Location:</span>
                        <span className="font-mono text-[#CBD5E1] font-medium">{formatTrackSpatial(t)}</span>
                      </div>
                      <div>
                        <span className="text-[#64748B] text-[10px] block">Duration:</span>
                        <span className="font-mono text-[#CBD5E1] font-medium">
                          {Math.floor((t.required_duration_minutes || 180) / 60)}h ({t.required_duration_minutes || 180}m)
                        </span>
                      </div>
                      <div>
                        <span className="text-[#64748B] text-[10px] block">Department:</span>
                        <span className="text-[#94A3B8] truncate block">{t.department?.replace(/_/g, ' ')}</span>
                      </div>
                      <div>
                        <span className="text-[#64748B] text-[10px] block">Machinery:</span>
                        <span className="text-[#94A3B8] truncate block">{t.machinery_required?.[0] || 'Track Machine'}</span>
                      </div>
                    </div>

                    {/* Card Actions */}
                    <div className="flex items-center justify-end gap-2 pt-1 border-t border-[#1E2D4A]/40">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(t.task_id);
                        }}
                        className="text-xs text-[#38BDF8] border-[#2D436D] hover:bg-[#141F36] h-8 px-3"
                      >
                        Inspect Details
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDigitalTwin(t.section_code || 'SEC-12');
                        }}
                        className="text-xs text-[#94A3B8] hover:text-white h-8 px-2.5"
                      >
                        3D Twin
                      </Button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Slide-In Contextual Work Order Detail Drawer (Rule 5 & 8) */}
      <ResponsiveDrawer
        isOpen={isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
        title={selectedTask ? `Work Order: ${selectedTask.task_code || selectedTask.task_id}` : 'Work Order Details'}
        subtitle={selectedTask?.title}
        badge={
          <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
            selectedTask?.priority === 'CRITICAL' || selectedTask?.task_id === 'TSK-0007'
              ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
              : 'bg-[#2563EB]/20 text-[#38BDF8] border-[#2563EB]/40'
          }`}>
            {selectedTask?.task_id === 'TSK-0007' ? 'UNPLACED CONFLICT' : 'SCHEDULED'}
          </span>
        }
        maxWidth="max-w-xl"
      >
        <div className="h-full">
          <EntityInspector
            task={selectedTask}
            scheduledInterval={selectedScheduled}
            conflictingTrains={[]}
            onClose={() => setIsInspectorOpen(false)}
            onOpenDigitalTwin={handleOpenDigitalTwin}
            isDrawer={true}
            hideHeader={true}
          />
        </div>
      </ResponsiveDrawer>

      {/* 3D Digital Twin Modal */}
      <DigitalTwinInspectionModal
        isOpen={isDigitalTwinOpen}
        onClose={() => setIsDigitalTwinOpen(false)}
        sectionCode={digitalTwinSection}
        sectionName="Northern Trunk Section"
        kmRange="km 209.0 – 301.0"
        workOrderTitle={selectedTask?.title}
        task={selectedTask}
      />
    </AppShell>
  );
}
