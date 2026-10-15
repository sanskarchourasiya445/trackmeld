'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

export interface SidebarContextType {
  isCollapsed: boolean;
  isMobileOpen: boolean;
  toggleCollapse: () => void;
  setCollapsed: (collapsed: boolean) => void;
  openMobile: () => void;
  closeMobile: () => void;
  toggleMobile: () => void;
  handleGlobalToggle: () => void;
}

const defaultContext: SidebarContextType = {
  isCollapsed: false,
  isMobileOpen: false,
  toggleCollapse: () => {},
  setCollapsed: () => {},
  openMobile: () => {},
  closeMobile: () => {},
  toggleMobile: () => {},
  handleGlobalToggle: () => {},
};

const SidebarContext = createContext<SidebarContextType>(defaultContext);

export const SidebarProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Restore persisted collapse state from localStorage on client mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('trackmeld_sidebar_collapsed');
      if (saved !== null) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setIsCollapsed(saved === 'true');
      }
    } catch {
      // Ignore localStorage errors (e.g. sandboxed iframe/storage blocked)
    }
  }, []);

  // Toggle desktop collapsed state and trigger window resize event
  const toggleCollapse = useCallback(() => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('trackmeld_sidebar_collapsed', String(next));
      } catch {
        // Ignore
      }
      // Broadcast resize event after CSS transition (200ms) so MapLibre GL & canvas resize
      setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
      }, 230);
      return next;
    });
  }, []);

  const setCollapsed = useCallback((collapsed: boolean) => {
    setIsCollapsed(collapsed);
    try {
      localStorage.setItem('trackmeld_sidebar_collapsed', String(collapsed));
    } catch {
      // Ignore
    }
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 230);
  }, []);

  const openMobile = useCallback(() => setIsMobileOpen(true), []);
  const closeMobile = useCallback(() => setIsMobileOpen(false), []);
  const toggleMobile = useCallback(() => setIsMobileOpen((prev) => !prev), []);

  // Combined toggle: on mobile (<1024px) toggles drawer; on desktop (>=1024px) toggles collapse
  const handleGlobalToggle = useCallback(() => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setIsMobileOpen((prev) => !prev);
    } else {
      toggleCollapse();
    }
  }, [toggleCollapse]);

  // Global keyboard shortcut Ctrl+B / Cmd+B to toggle sidebar collapse
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        handleGlobalToggle();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleGlobalToggle]);

  return (
    <SidebarContext.Provider
      value={{
        isCollapsed,
        isMobileOpen,
        toggleCollapse,
        setCollapsed,
        openMobile,
        closeMobile,
        toggleMobile,
        handleGlobalToggle,
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
};

export const useSidebar = () => {
  return useContext(SidebarContext);
};
