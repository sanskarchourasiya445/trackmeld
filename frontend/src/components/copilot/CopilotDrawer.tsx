'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  X,
  Send,
  AlertTriangle,
  Terminal,
  ExternalLink,
  Loader2,
  FileText,
  HelpCircle,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  askCopilot,
  CopilotQueryResponse,
  CopilotEvidenceItem,
} from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';

interface CopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTaskId?: string | null;
  onSelectTask?: (taskId: string) => void;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'copilot';
  text: string;
  evidence?: CopilotEvidenceItem[];
  provider?: string;
  timestamp: string;
  isError?: boolean;
}

const PRESET_QUERIES = [
  'Why was TSK-0007 not scheduled?',
  'Explain slot & safety buffers for TSK-0001',
  'What is the governance status of Plan Version 1?',
  'Explain railway rule RULE-STAT-RBP-1502C',
];

export const CopilotDrawer: React.FC<CopilotDrawerProps> = ({
  isOpen,
  onClose,
  selectedTaskId,
  onSelectTask,
}) => {
  const nextIdRef = useRef(1);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'copilot',
      text: `### TrackMeld Decision Support Copilot

I provide **evidence-grounded operational explanations** for maintenance possession planning.

Ask me about:
- **Task Scheduling Decisions**: Scheduled vs. unplaced tasks
- **Timetable & Section Contention**: Conflicting passenger express trains
- **Statutory Railway Rules**: General Rules, electrical isolation, block limits
- **Governance Status**: Plan reviews, DRM approvals, and audit trails

*Notice:* Strictly read-only (\`COMPLETED ≠ APPROVED\`). Cannot alter schedules or approve plans.`,
      provider: 'DETERMINISTIC_EVIDENCE_ENGINE',
      timestamp: 'INITIAL',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || inputValue).trim();
    if (!textToSend || isLoading) return;

    nextIdRef.current += 1;
    const userMsgId = `user-${nextIdRef.current}`;
    const timestampStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newMessages: ChatMessage[] = [
      ...messages,
      {
        id: userMsgId,
        sender: 'user',
        text: textToSend,
        timestamp: timestampStr,
      },
    ];
    setMessages(newMessages);
    setInputValue('');
    setIsLoading(true);

    try {
      const resp: CopilotQueryResponse = await askCopilot({
        prompt: textToSend,
        task_id: selectedTaskId || undefined,
      });

      nextIdRef.current += 1;
      setMessages([
        ...newMessages,
        {
          id: `copilot-${nextIdRef.current}`,
          sender: 'copilot',
          text: resp.answer,
          evidence: resp.evidence,
          provider: resp.provider_used,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err: unknown) {
      nextIdRef.current += 1;
      const errMsg = err instanceof Error ? err.message : 'Network error';
      setMessages([
        ...newMessages,
        {
          id: `error-${nextIdRef.current}`,
          sender: 'copilot',
          text: `**System Communication Warning:** Could not reach the backend Copilot service (${errMsg}).

In adherence to Indian Railways decision-support boundaries, the Copilot cannot infer, speculate, or fabricate ungrounded answers without verified database records.`,
          provider: 'LOCAL_GUARDRAIL',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEvidenceClick = (ev: CopilotEvidenceItem) => {
    if (ev.evidence_id.startsWith('TASK:')) {
      const tId = ev.evidence_id.replace('TASK:', '');
      if (onSelectTask) onSelectTask(tId);
    } else if (ev.evidence_id.startsWith('CONFLICT:')) {
      const tId = ev.evidence_id.replace('CONFLICT:', '');
      if (onSelectTask) onSelectTask(tId);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[460px] bg-[#0E0E12] border-l border-[#202024] shadow-2xl z-50 flex flex-col font-sans select-none animate-in slide-in-from-right duration-200">
      {/* 1. Header */}
      <div className="p-4 border-b border-[#202024] flex items-center justify-between bg-[#141418]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#2563EB]/20 border border-[#2563EB]/40 flex items-center justify-center text-[#38BDF8]">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-[#F5F5F5]">TrackMeld Copilot</span>
              <span className="text-[10px] font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.2 rounded font-bold">
                Read-Only
              </span>
            </div>
            <span className="text-[10px] font-mono text-[#71717A]">
              Evidence-Grounded Decision Support
            </span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-[#71717A] hover:text-white p-1 rounded hover:bg-[#1E1E24] transition-colors cursor-pointer"
          title="Close Copilot"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 2. Mandatory Governance Disclaimer Strip */}
      <div className="bg-[#141418] border-b border-[#202024] px-4 py-2 flex items-center gap-2 text-[10px] font-mono text-amber-300">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span className="truncate">
          <strong>COMPLETED ≠ APPROVED:</strong> Explanations cite verified telemetry. Cannot approve plans.
        </span>
      </div>

      {/* 3. Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${
              m.sender === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            {m.sender === 'user' ? (
              <div className="bg-[#2563EB] text-white px-3.5 py-2.5 rounded-lg max-w-[85%] text-xs leading-relaxed shadow-sm">
                {m.text}
              </div>
            ) : (
              <div
                className={`border p-3.5 rounded-lg max-w-[95%] space-y-2.5 shadow-sm ${
                  m.isError
                    ? 'bg-rose-950/20 border-rose-500/40 text-rose-100'
                    : 'bg-[#141418] border-[#202024] text-[#F5F5F5]'
                }`}
              >
                {/* Engine provenance badge */}
                <div className="flex items-center justify-between text-[10px] text-[#71717A] pb-1.5 border-b border-[#202024]">
                  <span className="flex items-center gap-1 text-[#38BDF8] font-mono">
                    <Terminal className="w-3 h-3" />
                    {m.provider || 'EVIDENCE_ENGINE'}
                  </span>
                  <span className="font-mono">{m.timestamp}</span>
                </div>

                {/* Markdown Formatted Body */}
                <MarkdownRenderer content={m.text} />

                {/* Evidence Citations */}
                {m.evidence && m.evidence.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-[#202024]/80 space-y-1.5">
                    <span className="text-[10px] uppercase text-[#71717A] font-bold block font-mono">
                      Verified Citations:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {m.evidence.map((ev) => (
                        <button
                          key={ev.evidence_id}
                          onClick={() => handleEvidenceClick(ev)}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#0E0E12] border border-[#29292F] text-[#38BDF8] hover:border-[#38BDF8] transition-colors cursor-pointer"
                          title={`${ev.title} (Source: ${ev.source_reference || 'db'})`}
                        >
                          <FileText className="w-2.5 h-2.5" />
                          <span>{ev.evidence_id}</span>
                          <ExternalLink className="w-2 h-2 text-[#71717A]" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-[#71717A] bg-[#141418] p-3 rounded border border-[#202024] w-fit font-mono">
            <Loader2 className="w-3.5 h-3.5 text-[#38BDF8] animate-spin" />
            <span>Consulting deterministic records & solver telemetry...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 4. Pre-populated Suggested Inquiries */}
      <div className="px-4 py-2 border-t border-[#202024] bg-[#0A0A0A] overflow-x-auto">
        <div className="flex items-center gap-1.5 text-[10px] font-mono">
          <span className="text-[#71717A] shrink-0 flex items-center gap-1">
            <HelpCircle className="w-3 h-3 text-[#38BDF8]" />
            Quick:
          </span>
          {PRESET_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              disabled={isLoading}
              className="shrink-0 bg-[#141418] hover:bg-[#1E1E24] text-[#A1A1AA] hover:text-white px-2 py-1 rounded border border-[#202024] transition-colors cursor-pointer"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* 5. Input Area */}
      <div className="p-3 border-t border-[#202024] bg-[#141418]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask why a task was unscheduled, check conflicts, or inspect rules..."
            disabled={isLoading}
            className="flex-1 bg-[#0A0A0A] border border-[#29292F] rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-[#71717A] focus:outline-hidden focus:border-[#2563EB]"
          />
          <Button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-3.5 h-8.5 rounded-lg cursor-pointer"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          </Button>
        </form>
      </div>
    </div>
  );
};
