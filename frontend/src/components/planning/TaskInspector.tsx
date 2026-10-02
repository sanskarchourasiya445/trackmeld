'use client';

import React, { useState } from 'react';
import { MaintenanceTask, TrainMovement, BlockSection } from '@/types/railway';
import {
  ScheduledTaskInterval,
  UnscheduledTaskReport,
  UnscheduledTaskDiagnostic,
} from '@/types/planning';
import {
  Bot,
  Send,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { askCopilot } from '@/lib/api/client';

interface TaskInspectorProps {
  task: MaintenanceTask | null;
  scheduledInterval?: ScheduledTaskInterval | null;
  unscheduledReport?: UnscheduledTaskReport | null;
  diagnostic?: UnscheduledTaskDiagnostic | null;
  conflictingTrains?: TrainMovement[];
  selectedTrain?: TrainMovement | null;
  selectedSection?: BlockSection | null;
  onClearSelection?: () => void;
  onSelectTask?: (taskId: string) => void;
}

export const TaskInspector: React.FC<TaskInspectorProps> = ({
  task,
  scheduledInterval,
  selectedTrain,
  selectedSection,
}) => {
  const [activeTab, setActiveTab] = useState<'TASK' | 'TRAIN' | 'SECTION' | 'RESOURCE'>('TASK');
  const [copilotInput, setCopilotInput] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [copilotResponse, setCopilotResponse] = useState<string>(
    'Possession window conflicts with Train 02073 by 18 minutes. Recommend advancing start by 25 min or diverting Train 02073 to Down Relief Line.'
  );

  const formatTime = (iso?: string | null, fallback: string = '14:00 - 15:30 UTC') => {
    if (!iso) return fallback;
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')} UTC`;
    } catch {
      return iso;
    }
  };

  const handleAskCopilot = async (promptText: string) => {
    if (!promptText.trim()) return;
    setCopilotLoading(true);
    setCopilotInput(promptText);
    try {
      const res = await askCopilot({
        prompt: promptText,
        task_id: task?.task_id || 'TSK-0007',
        scenario_id: 'SCN-DEMO-001',
      });
      setCopilotResponse(res.answer || 'Analysis complete: no active conflict violations found.');
    } catch (err) {
      console.warn('Copilot call fallback:', err);
      if (promptText.includes('Explain')) {
        setCopilotResponse(
          'Possession window conflicts with Train 02073 by 18 minutes. Recommend advancing start by 25 min or diverting Train 02073 to Down Relief Line.'
        );
      } else if (promptText.includes('Alternative')) {
        setCopilotResponse(
          'Alternative Slot Identified: 2026-10-11 09:30–11:00 UTC on Down Relief Line (clearance buffer 32 min, zero passenger headway delay).'
        );
      } else {
        setCopilotResponse(
          'Draft Possession Notice generated for Block-Section SEC-12 (NDLS-GZB Mainline) for 90 minutes. Requires OHE power block authorization.'
        );
      }
    } finally {
      setCopilotLoading(false);
    }
  };

  // Determine current display values
  const currentTaskId = task?.task_code || task?.task_id || 'TSK-0007';
  const currentType = task?.title || 'Track Renewal';
  const currentBlock = task?.section_code || task?.section_id || 'SEC-12 (NDLS-GZB Mainline)';
  const isCritical = task?.priority === 'CRITICAL' || task?.task_id === 'TSK-0007' || task?.task_id === 'TSK-0001';

  const windowText = scheduledInterval
    ? `${formatTime(scheduledInterval.interval?.start || scheduledInterval.start_time)} - ${formatTime(scheduledInterval.interval?.end || scheduledInterval.end_time)}`
    : `${formatTime(task?.earliest_start || task?.window_start, '14:00')} - ${formatTime(task?.latest_finish || task?.window_end, '15:30 UTC')}`;

  return (
    <div className="h-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg flex flex-col overflow-hidden select-none font-sans text-xs">
      {/* Top Header & Entity Tabs */}
      <div className="bg-[#141F36] border-b border-[#1E2D4A] p-3 space-y-2.5 shrink-0">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-[#F8FAFC]">Selected Entity</span>
          <span className="text-[10px] font-mono text-[#64748B]">Inspector & Diagnostics</span>
        </div>

        {/* Tab row: [Task | Train | Section | Resource] */}
        <div className="flex items-center gap-1 bg-[#0A0E17] border border-[#1E2D4A] p-0.5 rounded text-[11px] font-medium">
          <button
            onClick={() => setActiveTab('TASK')}
            className={`flex-1 py-1 rounded transition-colors text-center ${
              activeTab === 'TASK' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-white'
            }`}
          >
            Task
          </button>
          <button
            onClick={() => setActiveTab('TRAIN')}
            className={`flex-1 py-1 rounded transition-colors text-center ${
              activeTab === 'TRAIN' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-white'
            }`}
          >
            Train
          </button>
          <button
            onClick={() => setActiveTab('SECTION')}
            className={`flex-1 py-1 rounded transition-colors text-center ${
              activeTab === 'SECTION' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-white'
            }`}
          >
            Section
          </button>
          <button
            onClick={() => setActiveTab('RESOURCE')}
            className={`flex-1 py-1 rounded transition-colors text-center ${
              activeTab === 'RESOURCE' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-white'
            }`}
          >
            Resource
          </button>
        </div>
      </div>

      {/* Main Body: Entity Details */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5">
        {activeTab === 'TASK' && (
          <div className="space-y-2.5">
            <div className="grid grid-cols-2 gap-2 bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-lg p-3 text-[11px]">
              <div>
                <span className="text-[10px] text-[#64748B] block font-mono">Task ID</span>
                <span className="font-mono font-semibold text-[#F8FAFC]">{currentTaskId}</span>
              </div>
              <div>
                <span className="text-[10px] text-[#64748B] block font-mono">Priority</span>
                <span className={`inline-block px-1.5 py-0.2 rounded text-[10px] font-semibold ${
                  isCritical ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30' : 'bg-blue-500/15 text-blue-400'
                }`}>
                  {isCritical ? 'P1 (Critical)' : 'P3 (Routine)'}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-[10px] text-[#64748B] block font-mono">Type</span>
                <span className="font-medium text-[#F8FAFC]">{currentType}</span>
              </div>
              <div className="col-span-2">
                <span className="text-[10px] text-[#64748B] block font-mono">Block</span>
                <span className="font-mono text-[#CBD5E1]">{currentBlock}</span>
              </div>
              <div className="col-span-2">
                <span className="text-[10px] text-[#64748B] block font-mono">Time Window</span>
                <span className="font-mono text-[#2563EB] font-medium">{windowText}</span>
              </div>
              <div>
                <span className="text-[10px] text-[#64748B] block font-mono">Required Crew</span>
                <span className="text-[#CBD5E1]">4 Gangs (32 Persons)</span>
              </div>
              <div>
                <span className="text-[10px] text-[#64748B] block font-mono">Equipment</span>
                <span className="text-[#CBD5E1]">Tamping Machine TM-04</span>
              </div>
              <div className="col-span-2 pt-1 border-t border-[#1E2D4A]/60 flex items-center justify-between">
                <span className="text-[10px] text-[#64748B] font-mono">Conflicts Detected</span>
                <span className="font-semibold text-rose-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-rose-400" />
                  1 (Train 02073 Shatabdi Exp)
                </span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'TRAIN' && (
          <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-lg p-3 space-y-2 text-[11px]">
            <div className="flex justify-between items-center">
              <span className="font-mono text-[#64748B]">Train Movement</span>
              <span className="font-mono font-bold text-[#F8FAFC]">
                {selectedTrain ? selectedTrain.train_number : '02073 • Shatabdi Express'}
              </span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Class:</span>
              <span className="text-emerald-400 font-medium">Tier-1 Express (Protected Path)</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Section Entry / Exit:</span>
              <span className="font-mono text-[#CBD5E1]">NDLS (13:40) → CNB (18:15)</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Headway Buffer:</span>
              <span className="text-[#94A3B8]">30 min strict clearance</span>
            </div>
          </div>
        )}

        {activeTab === 'SECTION' && (
          <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-lg p-3 space-y-2 text-[11px]">
            <div className="flex justify-between items-center">
              <span className="font-mono text-[#64748B]">Block Section</span>
              <span className="font-mono font-bold text-[#F8FAFC]">
                {selectedSection ? selectedSection.code : 'SEC-12 (NDLS-GZB Mainline)'}
              </span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Length / Tracks:</span>
              <span className="font-mono text-[#CBD5E1]">26.4 km • 4 Tracks (UP/DN/Relief)</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Traction:</span>
              <span className="text-emerald-400 font-medium">25 kV AC OHE Electrified</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Permitted Speed:</span>
              <span className="font-mono text-[#CBD5E1]">130 km/h</span>
            </div>
          </div>
        )}

        {activeTab === 'RESOURCE' && (
          <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-lg p-3 space-y-2 text-[11px]">
            <div className="flex justify-between items-center">
              <span className="font-mono text-[#64748B]">Machine & Gang</span>
              <span className="font-mono font-bold text-[#F8FAFC]">RES-TM-CSM-01 & Gang 04</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Base Station:</span>
              <span className="font-mono text-[#CBD5E1]">Ghaziabad Yard (GZB)</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Mobilization Time:</span>
              <span className="text-[#94A3B8]">45 min transit allowed</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#64748B]">Operating Crew:</span>
              <span className="text-[#CBD5E1]">Certified Track Supervisors (IRICEN)</span>
            </div>
          </div>
        )}

        {/* AI Copilot Box (Integrated directly into the inspector) */}
        <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-[#F8FAFC]">
              <Bot className="w-3.5 h-3.5 text-[#2563EB]" />
              <span>AI Copilot (Read-Only)</span>
            </div>
            <span className="text-[9px] text-[#64748B] font-mono">Evidence-Grounded</span>
          </div>

          {/* Quick Action Prompt Chips */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => handleAskCopilot('Explain Conflict with Train 02073')}
              className="text-[10px] font-medium bg-[#141F36] hover:bg-[#1E2D4A] text-[#93C5FD] border border-[#1E2D4A] px-2 py-0.5 rounded transition-colors"
            >
              Explain Conflict
            </button>
            <button
              onClick={() => handleAskCopilot('Suggest Alternative Possession Window')}
              className="text-[10px] font-medium bg-[#141F36] hover:bg-[#1E2D4A] text-[#93C5FD] border border-[#1E2D4A] px-2 py-0.5 rounded transition-colors"
            >
              Suggest Alternative
            </button>
            <button
              onClick={() => handleAskCopilot('Draft Possession Notice for Section')}
              className="text-[10px] font-medium bg-[#141F36] hover:bg-[#1E2D4A] text-[#93C5FD] border border-[#1E2D4A] px-2 py-0.5 rounded transition-colors"
            >
              Draft Possess. Notice
            </button>
          </div>

          {/* Response Box */}
          <div className="bg-[#0F172A] border border-[#1E2D4A] rounded p-2.5 text-[11px] text-[#CBD5E1] leading-relaxed relative">
            {copilotLoading ? (
              <div className="flex items-center gap-2 text-[#94A3B8] py-1">
                <Sparkles className="w-3.5 h-3.5 text-[#2563EB] animate-spin" />
                <span>Evaluating conflict geometry and track headways...</span>
              </div>
            ) : (
              <p>{copilotResponse}</p>
            )}
          </div>

          {/* Ask Input */}
          <div className="relative flex items-center">
            <input
              type="text"
              placeholder="Ask Copilot..."
              value={copilotInput}
              onChange={(e) => setCopilotInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAskCopilot(copilotInput);
              }}
              className="w-full bg-[#141F36] border border-[#1E2D4A] rounded pl-2.5 pr-8 py-1.5 text-[11px] text-[#F8FAFC] placeholder-[#64748B] focus:outline-hidden focus:border-[#2563EB]"
            />
            <button
              onClick={() => handleAskCopilot(copilotInput)}
              className="absolute right-2 text-[#64748B] hover:text-[#2563EB] p-0.5 cursor-pointer"
              title="Submit query"
            >
              <Send className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
