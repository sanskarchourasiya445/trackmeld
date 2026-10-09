'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Bell,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  ExternalLink,
  Check,
  X,
  Clock,
} from 'lucide-react';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';

export interface OperationalNotification {
  id: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFORMATION';
  title: string;
  message: string;
  timestamp: string;
  source: string;
  targetUrl: string;
  isRead: boolean;
}

const INITIAL_NOTIFICATIONS: OperationalNotification[] = [
  {
    id: 'NOTIF-01',
    severity: 'CRITICAL',
    title: 'Headway Buffer Compression on SEC-12',
    message: 'Possession window for TSK-0007 creates 18-minute overlap with Express 12004. Safety rule RULE-HDW-01 violated.',
    timestamp: '10m ago (14:32 UTC)',
    source: 'CP-SAT Interval Engine',
    targetUrl: '/planning?subtab=CONFLICTS&conflict=CONF-HDW-01',
    isRead: false,
  },
  {
    id: 'NOTIF-02',
    severity: 'WARNING',
    title: 'Pending Four-Eyes Governance Approval',
    message: 'PlanVersion 1 candidate schedule awaiting secondary sign-off by designated approver ops_executive_officer.',
    timestamp: '25m ago (14:17 UTC)',
    source: 'Governance Pipeline',
    targetUrl: '/governance',
    isRead: false,
  },
  {
    id: 'NOTIF-03',
    severity: 'INFORMATION',
    title: 'CP-SAT Optimization Completed',
    message: 'Scenario A schedule solved in 1.48s. 29 of 30 tasks assigned feasible time intervals with 0 hard violations.',
    timestamp: '42m ago (14:00 UTC)',
    source: 'OR-Tools CP-SAT Worker',
    targetUrl: '/planning?subtab=TASKS',
    isRead: true,
  },
  {
    id: 'NOTIF-04',
    severity: 'INFORMATION',
    title: 'Independent Safety Firewall Certified',
    message: '13/13 mathematical validation checks passed (100% pass rate) with SHA-256 fingerprint bae346ecf3...',
    timestamp: '1h ago (13:42 UTC)',
    source: 'Independent Validator',
    targetUrl: '/governance',
    isRead: true,
  },
];

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({ isOpen, onClose }) => {
  const [notifications, setNotifications] = useState<OperationalNotification[]>(INITIAL_NOTIFICATIONS);
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'WARNING' | 'INFORMATION'>('ALL');

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  const filtered = notifications.filter((n) => {
    if (filter === 'ALL') return true;
    return n.severity === filter;
  });

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
  };

  const markItemRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
    );
  };

  return (
    <ResponsiveDrawer
      isOpen={isOpen}
      onClose={onClose}
      title="Operational Notifications"
      badge={
        unreadCount > 0 ? (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold border border-rose-500/40">
            {unreadCount} UNREAD
          </span>
        ) : (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/40">
            ALL ACKNOWLEDGED
          </span>
        )
      }
      maxWidth="max-w-md"
    >
      <div className="flex flex-col h-full text-xs font-sans">
        {/* Controls & Filter Tabs */}
        <div className="p-3.5 bg-[#0A0E17] border-b border-[#1E2D4A] flex items-center justify-between gap-2">
          <div className="flex items-center gap-1 bg-[#0F172A] p-1 rounded-lg border border-[#1E2D4A]">
            {(['ALL', 'CRITICAL', 'WARNING', 'INFORMATION'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`px-2.5 py-1 rounded text-[10.5px] font-semibold transition-colors ${
                  filter === tab
                    ? 'bg-[#2563EB] text-white shadow-xs'
                    : 'text-[#94A3B8] hover:text-white'
                }`}
              >
                {tab === 'INFORMATION' ? 'INFO' : tab}
              </button>
            ))}
          </div>

          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="text-[11px] text-[#38BDF8] hover:text-[#93C5FD] font-semibold flex items-center gap-1 cursor-pointer"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Acknowledge All</span>
            </button>
          )}
        </div>

        {/* Notifications List */}
        <div className="flex-1 overflow-y-auto divide-y divide-[#1E2D4A]/60 p-3 space-y-2">
          {filtered.length === 0 ? (
            <div className="py-16 text-center text-[#64748B]">
              <Bell className="w-8 h-8 mx-auto mb-2 text-[#1E2D4A]" />
              <p className="font-semibold text-xs text-[#94A3B8]">No notifications in this filter</p>
            </div>
          ) : (
            filtered.map((item) => (
              <div
                key={item.id}
                className={`p-3.5 rounded-xl border transition-all ${
                  item.isRead
                    ? 'bg-[#0A0E17]/60 border-[#1E2D4A]/50 text-[#94A3B8]'
                    : item.severity === 'CRITICAL'
                    ? 'bg-rose-950/20 border-rose-500/40 text-[#F8FAFC]'
                    : item.severity === 'WARNING'
                    ? 'bg-amber-950/20 border-amber-500/40 text-[#F8FAFC]'
                    : 'bg-[#0F172A] border-[#2563EB]/30 text-[#F8FAFC]'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {item.severity === 'CRITICAL' && (
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    )}
                    {item.severity === 'WARNING' && (
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    )}
                    {item.severity === 'INFORMATION' && (
                      <Info className="w-4 h-4 text-[#38BDF8] shrink-0" />
                    )}
                    <span className="font-bold text-xs">{item.title}</span>
                  </div>

                  {!item.isRead && (
                    <button
                      onClick={() => markItemRead(item.id)}
                      className="text-[#64748B] hover:text-white p-0.5"
                      title="Mark as read"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <p className="text-[11.5px] text-[#CBD5E1] mt-1.5 leading-relaxed">
                  {item.message}
                </p>

                <div className="flex items-center justify-between pt-2.5 mt-2 border-t border-[#1E2D4A]/60 text-[10.5px]">
                  <div className="flex items-center gap-2 text-[#64748B] font-mono">
                    <Clock className="w-3 h-3" />
                    <span>{item.timestamp}</span>
                    <span>•</span>
                    <span>{item.source}</span>
                  </div>

                  <Link
                    href={item.targetUrl}
                    onClick={() => {
                      markItemRead(item.id);
                      onClose();
                    }}
                    className="text-[#38BDF8] hover:text-white font-semibold flex items-center gap-1 group"
                  >
                    <span>View Context</span>
                    <ExternalLink className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </ResponsiveDrawer>
  );
};
