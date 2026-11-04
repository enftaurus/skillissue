import { useEffect, useRef, useCallback } from 'react';
import { api } from './api';

export interface TelemetryConfig {
  roundKey: string;
  candidateToken?: string;
  batchIntervalMs?: number;
  maxBatchSize?: number;
  enabled?: boolean;
}

export type KeyCategory =
  | 'printable'
  | 'enter'
  | 'tab'
  | 'backspace_delete'
  | 'arrow_navigation'
  | 'shortcut';

export type EventSource = 'typing' | 'paste' | 'suggest' | 'external';

export interface EditorTelemetryEvent {
  type:
    | 'key_down'
    | 'content_change'
    | 'paste'
    | 'cursor_move'
    | 'selection_change'
    | 'scroll'
    | 'blur'
    | 'focus'
    | 'visibility_change'
    | 'mouse_move';
  timestamp: number;
  key_category?: KeyCategory;
  source?: EventSource;
  range_offset?: number;
  range_length?: number;
  inserted_text?: string;
  inserted_length?: number;
  removed_length?: number;
  line_count_delta?: number;
  line?: number;
  column?: number;
  selection_length?: number;
  scroll_top?: number;
  state?: 'hidden' | 'visible';
  mouse_move_count?: number;
}

function categorizeKey(e: KeyboardEvent): KeyCategory {
  if (e.ctrlKey || e.metaKey || e.altKey) {
    return 'shortcut';
  }
  if (e.key === 'Enter') return 'enter';
  if (e.key === 'Tab') return 'tab';
  if (e.key === 'Backspace' || e.key === 'Delete') return 'backspace_delete';
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'PageUp', 'PageDown'].includes(e.key)) {
    return 'arrow_navigation';
  }
  return 'printable';
}

export function useEditorTelemetry({
  roundKey,
  candidateToken,
  batchIntervalMs = 5000,
  maxBatchSize = 500,
  enabled = true,
}: TelemetryConfig) {
  const eventQueue = useRef<EditorTelemetryEvent[]>([]);
  const seqRef = useRef<number>(0);
  const clientStartTsRef = useRef<number>(Date.now());
  const mouseMoveCountRef = useRef<number>(0);
  const isSuggestActiveRef = useRef<boolean>(false);
  const isPastingRef = useRef<boolean>(false);

  // Send batch to backend
  const flushQueue = useCallback(async () => {
    if (!enabled || eventQueue.current.length === 0) return;

    // Flush mouse move aggregate if any
    if (mouseMoveCountRef.current > 0) {
      eventQueue.current.push({
        type: 'mouse_move',
        timestamp: Date.now(),
        mouse_move_count: mouseMoveCountRef.current,
      });
      mouseMoveCountRef.current = 0;
    }

    const batchToSend = eventQueue.current.splice(0, maxBatchSize);
    if (batchToSend.length === 0) return;

    const payload = {
      round_key: roundKey,
      seq: seqRef.current,
      client_start_ts: clientStartTsRef.current,
      events: batchToSend,
    };

    seqRef.current += 1;

    try {
      const headers: Record<string, string> = {};
      if (candidateToken) {
        headers['Authorization'] = `Bearer ${candidateToken}`;
      }
      await api.post('/telemetry/editor', payload, { headers });
    } catch (err) {
      console.warn('[EditorTelemetry] Ingest batch warning:', err);
    }
  }, [enabled, roundKey, candidateToken, maxBatchSize]);

  // Periodic flush
  useEffect(() => {
    if (!enabled) return;
    const interval = setInterval(() => {
      flushQueue();
    }, batchIntervalMs);

    return () => clearInterval(interval);
  }, [enabled, batchIntervalMs, flushQueue]);

  // Flush on unload
  useEffect(() => {
    if (!enabled) return;
    const handleBeforeUnload = () => {
      flushQueue();
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [enabled, flushQueue]);

  // Window Focus / Blur & Visibility tracking
  useEffect(() => {
    if (!enabled) return;

    const handleBlur = () => {
      eventQueue.current.push({
        type: 'blur',
        timestamp: Date.now(),
      });
    };

    const handleFocus = () => {
      eventQueue.current.push({
        type: 'focus',
        timestamp: Date.now(),
      });
    };

    const handleVisibility = () => {
      eventQueue.current.push({
        type: 'visibility_change',
        timestamp: Date.now(),
        state: document.hidden ? 'hidden' : 'visible',
      });
    };

    const handleWindowMouseMove = () => {
      mouseMoveCountRef.current += 1;
    };

    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('mousemove', handleWindowMouseMove, { passive: true });

    return () => {
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('mousemove', handleWindowMouseMove);
    };
  }, [enabled]);

  // Monaco Editor integration helper
  const attachMonaco = useCallback(
    (editor: any, _monaco?: any) => {
      if (!enabled || !editor) return;

      // Track suggest widget opening/closing for autocomplete detection
      try {
        const suggestController = editor.getContribution('editor.contrib.suggestController');
        if (suggestController?.widget?.value) {
          suggestController.widget.value.onDidShow?.(() => {
            isSuggestActiveRef.current = true;
          });
          suggestController.widget.value.onDidHide?.(() => {
            setTimeout(() => {
              isSuggestActiveRef.current = false;
            }, 100);
          });
        }
      } catch (err) {
        // Suggest controller optional
      }

      // Key down listener (categorized only, no raw characters)
      const keyDisposable = editor.onKeyDown((e: any) => {
        const browserEvent = e.browserEvent as KeyboardEvent;
        const category = categorizeKey(browserEvent);

        eventQueue.current.push({
          type: 'key_down',
          timestamp: Date.now(),
          key_category: category,
          source: 'typing',
        });
      });

      // Paste listener
      const pasteDisposable = editor.onDidPaste?.((_e: any) => {
        isPastingRef.current = true;
        setTimeout(() => {
          isPastingRef.current = false;
        }, 100);
      });

      // Model Content Changes (Deltas)
      const changeDisposable = editor.onDidChangeModelContent((e: any) => {
        const now = Date.now();
        const changes = e.changes || [];

        for (const change of changes) {
          const insertedText = change.text || '';
          const rangeLength = change.rangeLength || 0;
          const rangeOffset = change.rangeOffset || 0;
          const lines = insertedText.split('\n');
          const lineCountDelta = lines.length - 1;

          let source: EventSource = 'typing';
          if (isPastingRef.current) {
            source = 'paste';
          } else if (isSuggestActiveRef.current) {
            source = 'suggest';
          }

          eventQueue.current.push({
            type: source === 'paste' ? 'paste' : 'content_change',
            timestamp: now,
            source,
            range_offset: rangeOffset,
            range_length: rangeLength,
            inserted_text: insertedText,
            inserted_length: insertedText.length,
            removed_length: rangeLength,
            line_count_delta: lineCountDelta,
          });
        }
      });

      // Cursor Position Changes
      const cursorDisposable = editor.onDidChangeCursorPosition((e: any) => {
        eventQueue.current.push({
          type: 'cursor_move',
          timestamp: Date.now(),
          line: e.position.lineNumber,
          column: e.position.column,
        });
      });

      // Selection Changes
      const selectionDisposable = editor.onDidChangeCursorSelection((e: any) => {
        const sel = e.selection;
        const selLen = Math.abs(
          (sel.endLineNumber - sel.startLineNumber) * 40 + (sel.endColumn - sel.startColumn)
        );
        if (selLen > 0) {
          eventQueue.current.push({
            type: 'selection_change',
            timestamp: Date.now(),
            selection_length: selLen,
          });
        }
      });

      // Scroll changes
      const scrollDisposable = editor.onDidScrollChange((e: any) => {
        if (e.scrollTopChanged) {
          eventQueue.current.push({
            type: 'scroll',
            timestamp: Date.now(),
            scroll_top: Math.round(e.scrollTop),
          });
        }
      });

      return () => {
        keyDisposable?.dispose();
        pasteDisposable?.dispose?.();
        changeDisposable?.dispose();
        cursorDisposable?.dispose();
        selectionDisposable?.dispose();
        scrollDisposable?.dispose();
      };
    },
    [enabled]
  );

  // Manual event logging for textarea or custom inputs
  const logContentChange = useCallback(
    (newText: string, prevText: string, rangeOffset: number, source: EventSource = 'typing') => {
      if (!enabled) return;
      const lengthDiff = newText.length - prevText.length;
      eventQueue.current.push({
        type: source === 'paste' ? 'paste' : 'content_change',
        timestamp: Date.now(),
        source,
        range_offset: rangeOffset,
        range_length: lengthDiff < 0 ? Math.abs(lengthDiff) : 0,
        inserted_text: lengthDiff > 0 ? newText.slice(rangeOffset, rangeOffset + lengthDiff) : '',
        inserted_length: Math.max(0, lengthDiff),
        removed_length: lengthDiff < 0 ? Math.abs(lengthDiff) : 0,
      });
    },
    [enabled]
  );

  const logKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!enabled) return;
      const category = categorizeKey(e.nativeEvent);
      eventQueue.current.push({
        type: 'key_down',
        timestamp: Date.now(),
        key_category: category,
        source: 'typing',
      });
    },
    [enabled]
  );

  const logPaste = useCallback(
    (pastedText: string, rangeOffset: number) => {
      if (!enabled) return;
      const lineCount = (pastedText.match(/\n/g) || []).length;
      eventQueue.current.push({
        type: 'paste',
        timestamp: Date.now(),
        source: 'paste',
        range_offset: rangeOffset,
        range_length: 0,
        inserted_text: pastedText,
        inserted_length: pastedText.length,
        line_count_delta: lineCount,
      });
    },
    [enabled]
  );

  return {
    attachMonaco,
    logContentChange,
    logKeyDown,
    logPaste,
    flushQueue,
  };
}
