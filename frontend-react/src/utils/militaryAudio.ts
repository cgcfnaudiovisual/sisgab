/**
 * Módulo de Efeitos Sonoros Militares & C2 Tático
 * Gerados nativamente via Web Audio API (sem dependência de arquivos externos)
 */

class MilitaryAudioEngine {
  private ctx: AudioContext | null = null;

  private getContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    try {
      if (!this.ctx || this.ctx.state === 'closed') {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        this.ctx = new AudioCtx();
      }
      if (this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
      return this.ctx;
    } catch {
      return null;
    }
  }

  /**
   * 🔊 Som Solene de Autenticação / Login Militar
   * Acorde harmônico e solene com decaimento suave
   */
  public playLoginSound() {
    const ctx = this.getContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      // Frequências para o acorde solene de autorização (C-Major expandido)
      const frequencies = [261.63, 392.0, 523.25, 659.25, 783.99]; // C4, G4, C5, E5, G5

      const masterGain = ctx.createGain();
      masterGain.gain.setValueAtTime(0.001, now);
      masterGain.gain.linearRampToValueAtTime(0.18, now + 0.08);
      masterGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.6);
      masterGain.connect(ctx.destination);

      frequencies.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const noteGain = ctx.createGain();

        osc.type = idx === 0 ? 'triangle' : 'sine';
        osc.frequency.setValueAtTime(freq, now + idx * 0.04);

        noteGain.gain.setValueAtTime(0.2, now);

        osc.connect(noteGain);
        noteGain.connect(masterGain);

        osc.start(now + idx * 0.04);
        osc.stop(now + 1.6);
      });
    } catch (e) {
      console.debug('Audio play not allowed or supported:', e);
    }
  }

  /**
   * ❌ Som de Alerta / Acesso Negado
   */
  public playAccessDeniedSound() {
    const ctx = this.getContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.linearRampToValueAtTime(150, now + 0.25);

      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.3);
    } catch (e) {
      console.debug('Audio play error:', e);
    }
  }

  /**
   * 📡 Bipe Tático de Comando / Confirmação
   */
  public playTacticalBeep() {
    const ctx = this.getContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, now); // La5

      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.12);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.12);
    } catch (e) {
      console.debug('Audio play error:', e);
    }
  }
}

export const militaryAudio = new MilitaryAudioEngine();