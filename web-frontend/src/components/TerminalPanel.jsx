import { useEffect, useRef, useState } from 'react';
import ScrambleText from './ScrambleText';

function formatTime(date) {
  const h = String(date.getHours()).padStart(2, '0');
  const m = String(date.getMinutes()).padStart(2, '0');
  const s = String(date.getSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function TerminalLine({ log, isLatest }) {
  const [displayedChars, setDisplayedChars] = useState(isLatest ? 0 : log.message.length);
  const fullText = `> [${formatTime(log.timestamp)}] ${log.message}`;

  useEffect(() => {
    if (!isLatest) {
      setDisplayedChars(fullText.length);
      return;
    }

    setDisplayedChars(0);
    let frame;
    let charIndex = 0;
    const startTime = performance.now();
    const charDelay = 12; // ms per character for fast typing

    const tick = (now) => {
      const elapsed = now - startTime;
      const targetChars = Math.min(Math.floor(elapsed / charDelay), fullText.length);

      if (targetChars !== charIndex) {
        charIndex = targetChars;
        setDisplayedChars(charIndex);
      }

      if (charIndex < fullText.length) {
        frame = requestAnimationFrame(tick);
      }
    };

    frame = requestAnimationFrame(tick);

    return () => {
      if (frame) cancelAnimationFrame(frame);
    };
  }, [fullText, isLatest]);

  return (
    <div className="terminal-line">
      {fullText.slice(0, displayedChars)}
    </div>
  );
}

export default function TerminalPanel({ logs }) {
  const bodyRef = useRef(null);

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="panel panel-bottom">
      <div className="terminal-header">
        <span className="header-bar"></span>
        <ScrambleText text="SYSTEM LOG" />
      </div>
      <div className="terminal-body" ref={bodyRef}>
        {logs.map((log, i) => (
          <TerminalLine
            key={i}
            log={log}
            isLatest={i === logs.length - 1}
          />
        ))}
        <span className="terminal-cursor"></span>
      </div>
    </div>
  );
}
