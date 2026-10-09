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
      <div className="flex-1 flex flex-col h-full overflow-hidden p-5 sm:p-7 lg:p-8 gap-5 bg-[#04070D] font-sans max-w-[1900px] w-full mx-auto">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0B101C] border border-[#1E2D4A] rounded-xl px-6 py-4 shrink-0 shadow-lg">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8]">
                <ClipboardList className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-[#F8FAFC]">Maintenance Work Orders & Requisitions</h1>
                <p className="text-xs text-[#94A3B8] mt-0.5">
                  Permanent Way (P-Way), S&T point machines, and 25 kV AC Traction electrical possession requests
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleOpenDigitalTwin(selectedTask?.section_code || 'SEC-12')}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#38BDF8] text-xs font-semibold h-8.5 px-3"
            >
              <Eye className="w-3.5 h-3.5 mr-1.5" />
              <span>Inspect in 3D Twin</span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsInspectorOpen((prev) => !prev)}
              className={`border-[#2D436D] text-xs font-semibold h-8.5 px-3 transition-colors ${
                isInspectorOpen ? 'bg-[#141F36] text-white border-[#2563EB]' : 'text-[#CBD5E1] hover:text-white'
              }`}
            >
              <PanelRight className="w-3.5 h-3.5 mr-1.5 text-[#38BDF8]" />
              <span>{isInspectorOpen ? 'Close Drawer' : 'Inspect Selected'}</span>
            </Button>
          </div>
        </div>

        {/* Operational Statistics Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 shrink-0">
          <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-xl p-4 space-y-1">
            <span className="text-[10px] font-mono text-[#64748B] uppercase font-bold tracking-wider">
              Total Requisitions
            </span>
            <div className="text-xl font-bold font-mono text-[#F8FAFC]">{tasks.length} Work Orders</div>
            <span className="text-[11px] text-[#94A3B8]">440 km Northern Trunk Corridor</span>
          </div>
          <div className="bg-[#0B101C] border border-emerald-500/30 rounded-xl p-4 space-y-1">
            <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold tracking-wider">
              Scheduled & Certified
            </span>
            <div className="text-xl font-bold font-mono text-emerald-400">{scheduledCount} Scheduled</div>
            <span className="text-[11px] text-[#94A3B8]">Passes all 13 safety firewall rules</span>
          </div>
          <div className="bg-[#0B101C] border border-rose-500/30 rounded-xl p-4 space-y-1">
            <span className="text-[10px] font-mono text-rose-400 uppercase font-bold tracking-wider">
              Conflicts / Unplaced
            </span>
            <div className="text-xl font-bold font-mono text-rose-400">{unplacedCount} Unplaced</div>
            <span className="text-[11px] text-[#94A3B8]">TSK-0007 requires headway shift</span>
          </div>
          <div className="bg-[#0B101C] border border-[#2563EB]/30 rounded-xl p-4 space-y-1">
            <span className="text-[10px] font-mono text-[#38BDF8] uppercase font-bold tracking-wider">
              Track Windows Blocked
            </span>
            <div className="text-xl font-bold font-mono text-[#38BDF8]">8 Possessions</div>
            <span className="text-[11px] text-[#94A3B8]">Coordinated with 50 express paths</span>
          </div>
        </div>

        {/* Filters and Search Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[#0B101C] border border-[#1E2D4A] rounded-xl p-3 shrink-0 text-xs">
          <div className="flex items-center gap-2.5 flex-1 max-w-lg bg-[#0F172A] border border-[#1E2D4A] rounded-lg px-3 py-2">
            <Search className="w-4 h-4 text-[#64748B] shrink-0" />
            <input
              type="text"
              placeholder="Search by Work Order ID, asset, task code, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent text-white placeholder-[#64748B] outline-none text-xs w-full font-mono"
            />
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Department Filter */}
            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              aria-label="Filter by department"
              className="bg-[#0F172A] border border-[#1E2D4A] text-[#CBD5E1] rounded-lg px-3 py-2 text-xs outline-none cursor-pointer"
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
              className="bg-[#0F172A] border border-[#1E2D4A] text-[#CBD5E1] rounded-lg px-3 py-2 text-xs outline-none cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="SCHEDULED">Scheduled (Certified)</option>
              <option value="UNSCHEDULED">Unplaced / Conflicts</option>
            </select>

            <span className="text-[11px] font-mono text-[#64748B] px-2">
              Showing {filteredTasks.length} of {tasks.length} orders
            </span>
          </div>
        </div>

        {/* Spacious Full-Width Table Workspace */}
        <div className="flex-1 min-h-0 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden flex flex-col shadow-sm">
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#0F172A] text-[#64748B] font-mono uppercase text-[10px] sticky top-0 border-b border-[#1E2D4A] z-10 tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">ID / Code</th>
                  <th className="py-3.5 px-4">Work Title</th>
                  <th className="py-3.5 px-4">Asset / Section</th>
                  <th className="py-3.5 px-4">Department</th>
                  <th className="py-3.5 px-4">Duration</th>
                  <th className="py-3.5 px-4">Priority</th>
                  <th className="py-3.5 px-4">Crew & Machinery</th>
                  <th className="py-3.5 px-4">Schedule Status</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2D4A]/50">
                {filteredTasks.map((t) => {
                  const isSelected = selectedTaskId === t.task_id;
                  const isUnplaced = t.task_id === 'TSK-0007';

                  return (
                    <tr
                      key={t.task_id}
                      onClick={() => handleRowClick(t.task_id)}
                      className={`hover:bg-[#141F36] cursor-pointer transition-colors ${
                        isSelected ? 'bg-[#141F36]/80 border-l-2 border-[#38BDF8]' : ''
                      }`}
                    >
                      <td className="py-4 px-4">
                        <span className="font-mono font-bold text-[#38BDF8] block">
                          {t.task_code || t.task_id}
                        </span>
                        <span className="text-[10px] text-[#64748B] font-mono">
                          {t.task_id}
                        </span>
                      </td>
                      <td className="py-4 px-4 font-medium text-[#F8FAFC] max-w-[280px]">
                        <span className="truncate block font-semibold text-sm leading-snug">{t.title}</span>
                        <span className="text-[11px] text-[#94A3B8] font-mono block mt-0.5">
                          {t.work_type}
                        </span>
                      </td>
                      <td className="py-4 px-4 font-mono text-[#CBD5E1]">
                        <span className="font-semibold block text-[#F8FAFC]">
                          {t.section_code || t.section_id}
                        </span>
                        <span className="text-[10px] text-[#38BDF8]">
                          {formatTrackSpatial(t)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-[#94A3B8] font-mono text-[11px]">
                        {t.department}
                      </td>
                      <td className="py-4 px-4 font-mono text-[#F8FAFC]">
                        {(t.required_duration_minutes || 180) / 60}h
                        <span className="text-[10px] text-[#64748B] ml-1">
                          ({t.required_duration_minutes || 180}m)
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded border ${
                          t.priority === 'CRITICAL' || isUnplaced
                            ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                            : 'bg-[#2563EB]/15 text-[#93C5FD] border-[#2563EB]/30'
                        }`}>
                          {t.priority || 'ROUTINE'}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-[#CBD5E1] text-[11px]">
                        <div className="font-medium">{t.crew_id || 'Gang A (6 Crew)'}</div>
                        <div className="text-[10px] text-[#64748B] truncate max-w-[160px]">
                          {t.machinery_required?.join(', ') || 'Track Machine'}
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span className={`inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2.5 py-1 rounded border ${
                          isUnplaced
                            ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${isUnplaced ? 'bg-rose-400' : 'bg-emerald-400'}`} />
                          {isUnplaced ? 'UNPLACED' : 'SCHEDULED'}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRowClick(t.task_id);
                          }}
                          className="text-xs text-[#38BDF8] hover:text-white mr-1 h-8"
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
                          className="text-xs text-[#94A3B8] hover:text-white h-8"
                        >
                          3D Twin
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
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
      />
    </AppShell>
  );
}
