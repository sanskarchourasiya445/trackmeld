'use client';

import React from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Lightweight, robust markdown renderer for TrackMeld AI Copilot explanations
 * and operational diagnostics. Formats headings, lists, bold text, inline code,
 * and evidence links cleanly without external dependencies.
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Split lines into blocks
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let currentList: { type: 'ul' | 'ol'; items: string[] } | null = null;

  const flushList = (keyPrefix: number) => {
    if (!currentList) return;
    if (currentList.type === 'ul') {
      elements.push(
        <ul key={`ul-${keyPrefix}`} className="list-disc list-inside space-y-1 my-1.5 pl-2 text-inherit">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {formatInlineText(item)}
            </li>
          ))}
        </ul>
      );
    } else {
      elements.push(
        <ol key={`ol-${keyPrefix}`} className="list-decimal list-inside space-y-1 my-1.5 pl-2 text-inherit">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {formatInlineText(item)}
            </li>
          ))}
        </ol>
      );
    }
    currentList = null;
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Empty lines
    if (!trimmed) {
      flushList(index);
      return;
    }

    // Headings
    if (trimmed.startsWith('### ')) {
      flushList(index);
      elements.push(
        <h3 key={`h3-${index}`} className="text-sm font-bold text-[#F8FAFC] mt-2.5 mb-1 tracking-tight">
          {formatInlineText(trimmed.replace('### ', ''))}
        </h3>
      );
      return;
    }
    if (trimmed.startsWith('## ')) {
      flushList(index);
      elements.push(
        <h2 key={`h2-${index}`} className="text-sm sm:text-base font-bold text-[#F8FAFC] mt-3 mb-1.5 tracking-tight">
          {formatInlineText(trimmed.replace('## ', ''))}
        </h2>
      );
      return;
    }
    if (trimmed.startsWith('# ')) {
      flushList(index);
      elements.push(
        <h1 key={`h1-${index}`} className="text-base sm:text-lg font-bold text-[#F8FAFC] mt-3.5 mb-2 tracking-tight">
          {formatInlineText(trimmed.replace('# ', ''))}
        </h1>
      );
      return;
    }

    // Bullet lists (- or *)
    const bulletMatch = trimmed.match(/^[-*]\s+(.+)/);
    if (bulletMatch) {
      if (!currentList || currentList.type !== 'ul') {
        flushList(index);
        currentList = { type: 'ul', items: [] };
      }
      currentList.items.push(bulletMatch[1]);
      return;
    }

    // Numbered lists (1. 2.)
    const numberMatch = trimmed.match(/^\d+\.\s+(.+)/);
    if (numberMatch) {
      if (!currentList || currentList.type !== 'ol') {
        flushList(index);
        currentList = { type: 'ol', items: [] };
      }
      currentList.items.push(numberMatch[1]);
      return;
    }

    // Normal paragraph line
    flushList(index);
    elements.push(
      <p key={`p-${index}`} className="leading-relaxed my-1 text-inherit">
        {formatInlineText(trimmed)}
      </p>
    );
  });

  flushList(lines.length);

  return <div className={`markdown-body space-y-1 text-xs leading-relaxed ${className}`}>{elements}</div>;
};

/**
 * Parses bold (**text**), italics (*text*), inline code (`code`), and links ([title](url))
 */
function formatInlineText(text: string): React.ReactNode {
  // Regex to split by markdown inline patterns: **bold**, `code`, *italic*, [link](url)
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g);

  return tokens.map((token, i) => {
    if (!token) return null;

    if (token.startsWith('**') && token.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-[#F8FAFC]">
          {token.slice(2, -2)}
        </strong>
      );
    }

    if (token.startsWith('`') && token.endsWith('`')) {
      return (
        <code
          key={i}
          className="font-mono text-[11px] px-1 py-0.5 rounded bg-[#0A0E17] text-[#38BDF8] border border-[#1E2D4A]"
        >
          {token.slice(1, -1)}
        </code>
      );
    }

    if (token.startsWith('*') && token.endsWith('*')) {
      return (
        <em key={i} className="italic text-[#CBD5E1]">
          {token.slice(1, -1)}
        </em>
      );
    }

    const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <span
          key={i}
          className="text-[#38BDF8] font-mono hover:underline cursor-pointer inline-flex items-center gap-0.5"
          title={`Evidence Reference: ${linkMatch[2]}`}
        >
          {linkMatch[1]}
        </span>
      );
    }

    return token;
  });
}
