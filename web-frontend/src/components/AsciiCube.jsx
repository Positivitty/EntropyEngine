import { useEffect, useRef, useState } from 'react';

const WIDTH = 55;
const HEIGHT = 28;

export default function AsciiCube({ sizeRatio = 1, isProcessing = false, isComplete = false, activeStage = null }) {
  const [frame, setFrame] = useState('');
  const angleRef = useRef({ a: 0, b: 0, c: 0 });
  const rafRef = useRef(null);
  const lastTimeRef = useRef(0);
  const glitchRef = useRef(0);
  const prevStageRef = useRef(null);

  // Detect stage transitions for glitch effect
  useEffect(() => {
    if (activeStage && activeStage !== prevStageRef.current) {
      glitchRef.current = 20; // 20 frames of glitch
    }
    prevStageRef.current = activeStage;
  }, [activeStage]);

  useEffect(() => {
    const fov = 40;
    const distFromCam = 30;
    const glitchChars = '░▒▓█▄▀│┤┐└┴┬├─┼';
    const faceChars = ['.', ',', '-', '~', ':', ';', '=', '!', '*', '#', '$', '@'];

    function rotateX(x, y, z, a) {
      const cos = Math.cos(a), sin = Math.sin(a);
      return [x, y * cos - z * sin, y * sin + z * cos];
    }
    function rotateY(x, y, z, a) {
      const cos = Math.cos(a), sin = Math.sin(a);
      return [x * cos + z * sin, y, -x * sin + z * cos];
    }
    function rotateZ(x, y, z, a) {
      const cos = Math.cos(a), sin = Math.sin(a);
      return [x * cos - y * sin, x * sin + y * cos, z];
    }

    function render(time) {
      if (time - lastTimeRef.current < 45) {
        rafRef.current = requestAnimationFrame(render);
        return;
      }
      lastTimeRef.current = time;

      // Cube size based on data ratio (min 2, max 9)
      const ratio = Math.max(0.15, Math.min(1, sizeRatio));
      const cubeSize = 2 + ratio * 7;

      // Spin speed: faster when processing
      const spinMultiplier = isProcessing ? 3 : isComplete ? 0.5 : 1;

      const { a, b, c } = angleRef.current;
      const buffer = Array.from({ length: HEIGHT }, () => Array(WIDTH).fill(' '));
      const zBuffer = Array.from({ length: HEIGHT }, () => Array(WIDTH).fill(-Infinity));

      const isGlitching = glitchRef.current > 0;
      if (isGlitching) glitchRef.current--;

      // Distortion during stage transitions
      const distort = isGlitching ? (Math.random() - 0.5) * 2 : 0;

      function project(x, y, z) {
        // Apply squeeze effect during encode stage
        let sy = y;
        if (activeStage === 'ENCODE' && isProcessing) {
          sy *= 0.7 + Math.sin(time * 0.01) * 0.15;
        }

        // Apply dissolve jitter during trim stage
        let jx = x, jz = z;
        if (activeStage === 'TRIM' && isProcessing) {
          const edge = Math.max(Math.abs(x), Math.abs(sy), Math.abs(z)) / cubeSize;
          if (edge > 0.85 && Math.random() > 0.6) return null;
        }

        let [rx, ry, rz] = rotateX(jx + distort, sy, jz, a);
        [rx, ry, rz] = rotateY(rx, ry, rz, b);
        [rx, ry, rz] = rotateZ(rx, ry, rz, c);
        rz += distFromCam;
        if (rz <= 0.1) return null;
        const px = Math.floor(WIDTH / 2 + (fov * rx) / rz);
        const py = Math.floor(HEIGHT / 2 - (fov * ry) / rz * 0.5);
        return { px, py, z: rz };
      }

      const step = 0.55;
      const faces = [
        (i, j) => [i, j, -cubeSize],
        (i, j) => [i, j, cubeSize],
        (i, j) => [i, -cubeSize, j],
        (i, j) => [i, cubeSize, j],
        (i, j) => [-cubeSize, i, j],
        (i, j) => [cubeSize, i, j],
      ];

      // Compress stage: rapidly collapse
      let scaleOverride = 1;
      if (activeStage === 'COMPRESS' && isProcessing) {
        scaleOverride = 0.6 + Math.sin(time * 0.008) * 0.2;
      }

      faces.forEach((face, fi) => {
        for (let i = -cubeSize; i <= cubeSize; i += step) {
          for (let j = -cubeSize; j <= cubeSize; j += step) {
            let [x, y, z] = face(i, j);
            x *= scaleOverride;
            y *= scaleOverride;
            z *= scaleOverride;

            const p = project(x, y, z);
            if (!p) continue;
            const { px, py, z: pz } = p;
            if (px < 0 || px >= WIDTH || py < 0 || py >= HEIGHT) continue;
            const invZ = 1 / pz;
            if (invZ > zBuffer[py][px]) {
              zBuffer[py][px] = invZ;
              if (isGlitching && Math.random() > 0.7) {
                buffer[py][px] = glitchChars[Math.floor(Math.random() * glitchChars.length)];
              } else if (isProcessing && Math.random() > 0.92) {
                // Scramble some chars during processing
                buffer[py][px] = faceChars[Math.floor(Math.random() * faceChars.length)];
              } else {
                const charIdx = Math.min(fi * 2 + Math.floor(Math.abs(i + j) % 2), faceChars.length - 1);
                buffer[py][px] = faceChars[charIdx];
              }
            }
          }
        }
      });

      setFrame(buffer.map(row => row.join('')).join('\n'));

      angleRef.current.a += 0.012 * spinMultiplier;
      angleRef.current.b += 0.016 * spinMultiplier;
      angleRef.current.c += 0.006 * spinMultiplier;

      rafRef.current = requestAnimationFrame(render);
    }

    rafRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(rafRef.current);
  }, [sizeRatio, isProcessing, isComplete, activeStage]);

  // Glow intensity based on state
  const glowOpacity = isProcessing ? 0.6 : isComplete ? 0.5 : 0.3;
  const color = isComplete ? '#00ff41' : isProcessing ? '#00d4ff' : '#00ff41';

  return (
    <pre style={{
      fontFamily: "'Share Tech Mono', monospace",
      fontSize: '10px',
      lineHeight: '1.05',
      color: color,
      opacity: isProcessing ? 0.5 : 0.3,
      textAlign: 'center',
      userSelect: 'none',
      pointerEvents: 'none',
      margin: '0 auto',
      whiteSpace: 'pre',
      textShadow: `0 0 8px rgba(0, 255, 65, ${glowOpacity})`,
      transition: 'opacity 0.5s ease, color 0.5s ease',
    }}>
      {frame}
    </pre>
  );
}
