import React from 'react';

/**
 * Minimal, XSS-safe markdown renderer for interviewer messages (headings, bold, inline code,
 * fenced code, bullet lists, paragraphs). Builds React elements only: no HTML injection.
 */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];
    if (token.startsWith('**')) {
      nodes.push(<strong key={`${keyPrefix}-b${i}`} className="font-semibold">{token.slice(2, -2)}</strong>);
    } else {
      nodes.push(
        <code key={`${keyPrefix}-c${i}`} className="px-1 py-0.5 rounded bg-black/5 font-mono text-[0.85em]">
          {token.slice(1, -1)}
        </code>
      );
    }
    last = match.index + token.length;
    i += 1;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export const SimpleMarkdown: React.FC<{ text: string; className?: string }> = ({ text, className }) => {
  const blocks: React.ReactNode[] = [];
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n');
  let i = 0;
  let para: string[] = [];
  let list: string[] = [];

  const flushPara = () => {
    if (para.length) {
      const k = `p${blocks.length}`;
      blocks.push(
        <p key={k} className="whitespace-pre-wrap">
          {renderInline(para.join('\n'), k)}
        </p>
      );
      para = [];
    }
  };
  const flushList = () => {
    if (list.length) {
      const k = `l${blocks.length}`;
      blocks.push(
        <ul key={k} className="list-disc pl-5 space-y-0.5">
          {list.map((item, idx) => (
            <li key={`${k}-${idx}`}>{renderInline(item, `${k}-${idx}`)}</li>
          ))}
        </ul>
      );
      list = [];
    }
  };

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim().startsWith('```')) {
      flushPara();
      flushList();
      const code: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        code.push(lines[i]);
        i += 1;
      }
      i += 1; // closing fence
      blocks.push(
        <pre key={`pre${blocks.length}`} className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs font-mono overflow-x-auto">
          <code>{code.join('\n')}</code>
        </pre>
      );
      continue;
    }
    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    if (heading) {
      flushPara();
      flushList();
      const k = `h${blocks.length}`;
      blocks.push(
        <p key={k} className="font-bold text-base">
          {renderInline(heading[2], k)}
        </p>
      );
    } else if (/^\s*[-*•]\s+/.test(line)) {
      flushPara();
      list.push(line.replace(/^\s*[-*•]\s+/, ''));
    } else if (!line.trim()) {
      flushPara();
      flushList();
    } else {
      flushList();
      para.push(line.replace(/\s+$/, ''));
    }
    i += 1;
  }
  flushPara();
  flushList();
  return <div className={`space-y-2 ${className || ''}`}>{blocks}</div>;
};
