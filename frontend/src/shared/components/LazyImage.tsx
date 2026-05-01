import { useEffect, useRef, useState, type CSSProperties } from "react";
import { decode } from "blurhash";

interface LazyImageProps {
  src?: string | null;
  blurHash?: string;
  alt: string;
  className?: string;
  fallbackClassName?: string;
  fallbackStyle?: CSSProperties;
}

const DEFAULT_BLUR = "LEHV6nWB2yk8pyo0adR*.7kCMdnj";

export default function LazyImage({
  src,
  blurHash = DEFAULT_BLUR,
  alt,
  className = "",
  fallbackClassName = "",
  fallbackStyle,
}: LazyImageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(!src);

  useEffect(() => {
    if (!canvasRef.current) return;
    try {
      const pixels = decode(blurHash, 32, 32);
      const ctx = canvasRef.current.getContext("2d");
      if (!ctx) return;
      const imageData = ctx.createImageData(32, 32);
      imageData.data.set(pixels);
      ctx.putImageData(imageData, 0, 0);
    } catch {
      setFailed(true);
    }
  }, [blurHash]);

  return (
    <div className={`relative overflow-hidden ${fallbackClassName}`} style={fallbackStyle}>
      <canvas
        ref={canvasRef}
        width={32}
        height={32}
        className="absolute inset-0 h-full w-full scale-110 object-cover"
        style={{ opacity: loaded || failed ? 0 : 1 }}
      />
      {src && !failed ? (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          className={`${className} transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center px-2 text-center text-[10px] font-semibold text-sf-dark/70">
          {alt.slice(0, 18)}
        </div>
      )}
    </div>
  );
}
