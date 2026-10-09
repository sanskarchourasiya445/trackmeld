'use client';

import React, { useState } from 'react';
import { LandingNavbar } from '@/components/landing-3d/LandingNavbar';
import { LandingHero3D } from '@/components/landing-3d/LandingHero3D';
import { SectionDigitalTwin } from '@/components/landing-3d/SectionDigitalTwin';
import { SectionConstraints } from '@/components/landing-3d/SectionConstraints';
import { SectionOptimization } from '@/components/landing-3d/SectionOptimization';
import { SectionValidation } from '@/components/landing-3d/SectionValidation';
import { SectionCopilot } from '@/components/landing-3d/SectionCopilot';
import { SectionPlanComparison } from '@/components/landing-3d/SectionPlanComparison';
import { SectionArchitecture } from '@/components/landing-3d/SectionArchitecture';
import { SectionFooterCTA } from '@/components/landing-3d/SectionFooterCTA';
import { DemoRequestModal } from '@/components/landing-3d/DemoRequestModal';

/**
 * TrackMeld Canonical Homepage (/)
 * Official 3D Railway Digital Twin & Possession Planning Platform
 */
export default function HomePage() {
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);

  return (
    <main className="min-h-screen bg-[#04070D] text-slate-100 selection:bg-sky-500/30 selection:text-sky-200 antialiased overflow-x-hidden">
      {/* Fixed Enterprise Navigation Bar */}
      <LandingNavbar onRequestDemo={() => setIsDemoModalOpen(true)} />

      {/* Hero Section: 3D Digital Twin Viewport & Real-time Telemetry HUD */}
      <LandingHero3D onRequestDemo={() => setIsDemoModalOpen(true)} />

      {/* Section 2: Meso-Topology & Layered Railway Reality */}
      <SectionDigitalTwin />

      {/* Section 3: Hard Safety Constraints & Interlocking Conflict Matrix */}
      <SectionConstraints />

      {/* Section 4: CP-SAT Discrete Interval Mathematical Solver Engine */}
      <SectionOptimization />

      {/* Section 5: Independent 13-Category Safety Validation Firewall */}
      <SectionValidation />

      {/* Section 6: Grounded, Read-Only Explainable AI Copilot Terminal */}
      <SectionCopilot />

      {/* Section 7: Three-Way Plan Comparison Matrix (Manual vs TrackMeld vs Whole-Section) */}
      <SectionPlanComparison />

      {/* Section 8: Inviolable End-to-End Governance Architecture */}
      <SectionArchitecture />

      {/* Section 9: Executive CTA & Railway Operational Governance Footer */}
      <SectionFooterCTA onOpenDemo={() => setIsDemoModalOpen(true)} />

      {/* Enterprise Architecture Dossier & Demo Request Modal */}
      <DemoRequestModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
      />
    </main>
  );
}
