import { useMemo } from "react";

export function useAudioAlert() {
  return useMemo(() => ({
    newOrder() {
      try {
        const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
        if (!AudioContextClass) return;
        const ctx = new AudioContextClass();
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();
        oscillator.frequency.value = 720;
        gain.gain.value = 0.04;
        oscillator.connect(gain);
        gain.connect(ctx.destination);
        oscillator.start();
        oscillator.stop(ctx.currentTime + 0.16);
        oscillator.onended = () => void ctx.close();
      } catch {
        // Browsers can block audio until the page has user interaction.
      }
    },
  }), []);
}
