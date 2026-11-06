// Live voice client for /api/v1/voice/ws/{interviewId} (Nova Sonic relay, ADR 0025).
// Mic -> AudioWorklet -> 16 kHz s16 PCM (100 ms chunks) -> WebSocket; 24 kHz PCM from the server is
// scheduled gaplessly and dropped instantly on barge-in. Audio is never stored.

export type LiveVoiceState = 'idle' | 'connecting' | 'listening' | 'interviewer' | 'ended' | 'error';

export interface LiveVoiceCallbacks {
  onState?: (state: LiveVoiceState) => void;
  onCaption?: (role: 'user' | 'assistant', text: string) => void;
  onTurn?: (turn: { user: string; assistant: string; kind?: string; message_id?: string }) => void;
  onCompleted?: () => void;
  onError?: (code: string, message: string) => void;
  onLevel?: (level: number) => void;
}

const WORKLET_SOURCE = `
class PcmDownsampler extends AudioWorkletProcessor {
  constructor() { super(); this.ratio = sampleRate / 16000; this.buf = []; this.acc = 0; }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    let sum = 0;
    for (let i = 0; i < ch.length; i++) {
      sum += ch[i] * ch[i];
      this.acc += 1;
      if (this.acc >= this.ratio) { this.acc -= this.ratio; this.buf.push(ch[i]); }
    }
    if (this.buf.length >= 1600) {
      const out = new Int16Array(this.buf.length);
      for (let i = 0; i < this.buf.length; i++) {
        const s = Math.max(-1, Math.min(1, this.buf[i]));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage({ pcm: out.buffer, level: Math.sqrt(sum / ch.length) }, [out.buffer]);
      this.buf = [];
    }
    return true;
  }
}
registerProcessor('pcm-downsampler', PcmDownsampler);
`;

function toBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = '';
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

function fromBase64(b64: string): Int16Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Int16Array(bytes.buffer);
}

export function liveVoiceSupported(): boolean {
  return typeof window !== 'undefined' && 'AudioWorkletNode' in window && !!navigator.mediaDevices?.getUserMedia && 'WebSocket' in window;
}

export class LiveVoiceClient {
  private ws: WebSocket | null = null;
  private micCtx: AudioContext | null = null;
  private playCtx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;
  private sources: AudioBufferSourceNode[] = [];
  private nextStart = 0;
  private state: LiveVoiceState = 'idle';

  constructor(private interviewId: string, private cb: LiveVoiceCallbacks = {}) {}

  private setState(s: LiveVoiceState) {
    this.state = s;
    this.cb.onState?.(s);
  }

  async start(token: string, voice?: string) {
    this.setState('connecting');
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
    } catch (e: any) {
      this.fail('MIC_DENIED', 'Microphone access was denied.');
      return;
    }
    this.micCtx = new AudioContext();
    this.playCtx = new AudioContext({ sampleRate: 24000 });
    const url = URL.createObjectURL(new Blob([WORKLET_SOURCE], { type: 'application/javascript' }));
    await this.micCtx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${window.location.host}/api/v1/voice/ws/${this.interviewId}`);
    this.ws.onopen = () => this.ws?.send(JSON.stringify({ type: 'auth', token, voice }));
    this.ws.onmessage = (ev) => this.handle(JSON.parse(ev.data));
    this.ws.onclose = () => {
      if (this.state !== 'error' && this.state !== 'ended') this.setState('ended');
      this.teardownAudio();
    };
    this.ws.onerror = () => this.fail('VOICE_FAILED', 'Live voice connection failed.');
  }

  private startMic() {
    if (!this.micCtx || !this.stream) return;
    const src = this.micCtx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.micCtx, 'pcm-downsampler');
    this.node.port.onmessage = (e) => {
      this.cb.onLevel?.(Math.min(1, (e.data.level || 0) * 4));
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'audio', data: toBase64(e.data.pcm) }));
      }
    };
    src.connect(this.node);
  }

  private handle(m: any) {
    switch (m.type) {
      case 'ready':
        this.startMic();
        this.setState('listening');
        break;
      case 'audio':
        this.play(m.data);
        break;
      case 'interrupt':
        this.stopPlayback();
        this.setState('listening');
        break;
      case 'caption':
        this.cb.onCaption?.(m.role, m.text);
        break;
      case 'turn':
        this.cb.onTurn?.(m);
        break;
      case 'completed':
        this.cb.onCompleted?.();
        // Let the closing line finish before hanging up.
        setTimeout(() => this.stop(), Math.max(0, (this.nextStart - (this.playCtx?.currentTime || 0)) * 1000) + 300);
        break;
      case 'error':
        this.fail(m.code, m.message);
        break;
    }
  }

  private play(b64: string) {
    if (!this.playCtx) return;
    const pcm = fromBase64(b64);
    const buffer = this.playCtx.createBuffer(1, pcm.length, 24000);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) data[i] = pcm[i] / 0x8000;
    const src = this.playCtx.createBufferSource();
    src.buffer = buffer;
    src.connect(this.playCtx.destination);
    const now = this.playCtx.currentTime;
    this.nextStart = Math.max(this.nextStart, now + 0.03);
    src.start(this.nextStart);
    this.nextStart += buffer.duration;
    this.sources.push(src);
    src.onended = () => {
      this.sources = this.sources.filter((s) => s !== src);
      if (!this.sources.length && this.state === 'interviewer') this.setState('listening');
    };
    if (this.state !== 'interviewer') this.setState('interviewer');
  }

  private stopPlayback() {
    this.sources.forEach((s) => {
      try {
        s.stop();
      } catch {
        /* already stopped */
      }
    });
    this.sources = [];
    this.nextStart = 0;
  }

  private fail(code: string, message: string) {
    this.setState('error');
    this.cb.onError?.(code, message);
    this.stop();
  }

  private teardownAudio() {
    this.stopPlayback();
    this.node?.disconnect();
    this.node = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.micCtx?.close().catch(() => {});
    this.playCtx?.close().catch(() => {});
    this.micCtx = null;
    this.playCtx = null;
  }

  stop() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({ type: 'stop' }));
      } catch {
        /* closing */
      }
      this.ws.close();
    }
    this.ws = null;
    this.teardownAudio();
    if (this.state !== 'error') this.setState('ended');
  }
}
