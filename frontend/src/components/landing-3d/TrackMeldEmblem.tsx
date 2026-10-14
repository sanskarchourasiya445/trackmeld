'use client';

import React from 'react';

interface TrackMeldEmblemProps {
  className?: string;
  size?: number;
}

/**
 * Authentic TrackMeld Brand Emblem
 * Features:
 * - Rounded dark navy squircle badge with electric cyan/blue glowing perimeter border
 * - 3D isometric railway track segment with extruded UIC steel rails & sleepers
 * - Orbital telemetry ring encircling the track with dual luminous satellite sensor nodes
 */
export const TrackMeldEmblem: React.FC<TrackMeldEmblemProps> = ({
  className = 'w-8 h-8',
  size,
}) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 120 120"
      width={size}
      height={size}
      className={className}
      fill="none"
      aria-label="TrackMeld Brand Emblem"
    >
      <defs>
        <linearGradient id="emblemBorder" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00F0FF" />
          <stop offset="50%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#1D4ED8" />
        </linearGradient>
        <linearGradient id="railTop" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#93C5FD" />
        </linearGradient>
        <linearGradient id="railSide" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0284C7" />
          <stop offset="100%" stopColor="#1E3A8A" />
        </linearGradient>
        <linearGradient id="sleeperGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0284C7" />
          <stop offset="100%" stopColor="#0F2856" />
        </linearGradient>
        <filter id="nodeGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Dark Navy Squircle Background with Glowing Cyan/Blue Border */}
      <rect
        x="6"
        y="6"
        width="108"
        height="108"
        rx="26"
        fill="#070E1C"
        stroke="url(#emblemBorder)"
        strokeWidth="3.5"
      />

      {/* Orbital Telemetry Ring Behind/Around Track */}
      <path
        d="M 32 37 C 22 47, 24 68, 38 78 C 50 86, 68 86, 82 76"
        fill="none"
        stroke="#00E5FF"
        strokeWidth="2.5"
        strokeLinecap="round"
        opacity="0.9"
      />
      <path
        d="M 88 64 C 98 52, 94 34, 80 26 C 68 18, 50 20, 38 30"
        fill="none"
        stroke="#00E5FF"
        strokeWidth="2.5"
        strokeLinecap="round"
        opacity="0.9"
      />

      {/* Orbital Telemetry Satellite Nodes */}
      <circle cx="35" cy="34" r="4.5" fill="#FFFFFF" filter="url(#nodeGlow)" />
      <circle cx="35" cy="34" r="2.5" fill="#00F0FF" />

      <circle cx="85" cy="73" r="4.5" fill="#FFFFFF" filter="url(#nodeGlow)" />
      <circle cx="85" cy="73" r="2.5" fill="#00F0FF" />

      {/* 3D Isometric Railway Track Structure */}
      {/* 5 Sleepers (Ties) */}
      <g opacity="0.95">
        {/* Tie 1 */}
        <polygon points="32,67 44,57 48,60 36,70" fill="url(#sleeperGrad)" />
        <polygon points="32,67 36,70 36,73 32,70" fill="#0369A1" />
        <polygon points="36,70 48,60 48,63 36,73" fill="#075985" />

        {/* Tie 2 */}
        <polygon points="41,59 53,49 57,52 45,62" fill="url(#sleeperGrad)" />
        <polygon points="41,59 45,62 45,65 41,62" fill="#0369A1" />
        <polygon points="45,62 57,52 57,55 45,65" fill="#075985" />

        {/* Tie 3 */}
        <polygon points="50,51 62,41 66,44 54,54" fill="url(#sleeperGrad)" />
        <polygon points="50,51 54,54 54,57 50,54" fill="#0369A1" />
        <polygon points="54,54 66,44 66,47 54,57" fill="#075985" />

        {/* Tie 4 */}
        <polygon points="59,43 71,33 75,36 63,46" fill="url(#sleeperGrad)" />
        <polygon points="59,43 63,46 63,49 59,46" fill="#0369A1" />
        <polygon points="63,46 75,36 75,39 63,49" fill="#075985" />

        {/* Tie 5 */}
        <polygon points="68,35 80,25 84,28 72,38" fill="url(#sleeperGrad)" />
        <polygon points="68,35 72,38 72,41 68,38" fill="#0369A1" />
        <polygon points="72,38 84,28 84,31 72,41" fill="#075985" />
      </g>

      {/* Rail 1: Left / Upper Extruded Steel Rail */}
      <polygon points="27,72 80,29 84,32 31,75" fill="url(#railTop)" />
      <polygon points="27,72 31,75 31,79 27,76" fill="#38BDF8" />
      <polygon points="27,72 27,76 80,33 80,29" fill="url(#railSide)" />

      {/* Rail 2: Right / Lower Extruded Steel Rail */}
      <polygon points="41,83 94,40 98,43 45,86" fill="url(#railTop)" />
      <polygon points="41,83 45,86 45,90 41,87" fill="#38BDF8" />
      <polygon points="41,83 41,87 94,44 94,40" fill="url(#railSide)" />
    </svg>
  );
};
