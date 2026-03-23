import { useState, useEffect, useRef } from 'react';

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*';

export default function ScrambleText({ text, className, style }) {
  const [display, setDisplay] = useState(text);
  const intervalRef = useRef(null);
  const iterationRef = useRef(0);

  useEffect(() => {
    iterationRef.current = 0;

    intervalRef.current = setInterval(() => {
      setDisplay(
        text
          .split('')
          .map((char, i) => {
            if (char === ' ') return ' ';
            if (i < iterationRef.current) return text[i];
            return CHARS[Math.floor(Math.random() * CHARS.length)];
          })
          .join('')
      );

      iterationRef.current += 1 / 2;

      if (iterationRef.current >= text.length) {
        clearInterval(intervalRef.current);
        setDisplay(text);
      }
    }, 40);

    return () => clearInterval(intervalRef.current);
  }, [text]);

  return <span className={className} style={style}>{display}</span>;
}
