// Cross-Browser Cloud Neural Speech Engine
// Studio-quality Text-to-Speech (HTML5 Audio streaming via /api/v1/audio/tts)
// Cloud-grade Speech-to-Text via Backend Faster-Whisper & AWS Transcribe (/api/v1/audio/stt)
// Completely free from unreliable browser SpeechRecognition

import { api } from './api';

export interface VoiceOption {
  id: string;
  name: string;
  gender: string;
  accent: string;
  provider: string;
  description: string;
}

export const DEFAULT_VOICES: VoiceOption[] = [
  {
    id: 'aws-polly-matthew',
    name: 'Matthew (AWS Polly Neural)',
    gender: 'Male',
    accent: 'US',
    provider: 'aws-polly',
    description: 'Senior Staff Engineer & Hiring Manager. Authoritative, direct, crisp.',
  },
  {
    id: 'aws-polly-kajal',
    name: 'Kajal (AWS Polly Neural)',
    gender: 'Female',
    accent: 'India',
    provider: 'aws-polly',
    description: 'Principal Systems Architect. Natural Indian English rhythm, methodical and sharp.',
  },
  {
    id: 'aws-polly-ruth',
    name: 'Ruth (AWS Polly Generative)',
    gender: 'Female',
    accent: 'US',
    provider: 'aws-polly',
    description: 'AWS Polly Generative Engine. Ultra-realistic conversational human prosody.',
  },
  {
    id: 'aws-polly-arthur',
    name: 'Arthur (AWS Polly Neural)',
    gender: 'Male',
    accent: 'UK',
    provider: 'aws-polly',
    description: 'Technical Lead. Dry, analytical, and measured British accent.',
  },
  {
    id: 'en-US-ChristopherNeural',
    name: 'Christopher (Studio Neural)',
    gender: 'Male',
    accent: 'US',
    provider: 'edge-azure',
    description: 'Senior Staff Engineer & Hiring Manager. Direct, crisp, zero artificial praise.',
  },
  {
    id: 'en-US-JennyNeural',
    name: 'Jenny (Studio Neural)',
    gender: 'Female',
    accent: 'US',
    provider: 'edge-azure',
    description: 'Lead Systems Architect. Clear, precise, articulate.',
  },
  {
    id: 'en-IN-PrabhatNeural',
    name: 'Prabhat (Studio Neural)',
    gender: 'Male',
    accent: 'India',
    provider: 'edge-azure',
    description: 'Senior Technical Lead. Natural Indian English rhythm, methodical and sharp.',
  },
  {
    id: 'en-IN-NeerjaNeural',
    name: 'Neerja (Studio Neural)',
    gender: 'Female',
    accent: 'India',
    provider: 'edge-azure',
    description: 'Principal Systems Engineer. Authentic Indian English cadence and clarity.',
  },
  {
    id: 'en-GB-RyanNeural',
    name: 'Ryan (Studio Neural)',
    gender: 'Male',
    accent: 'UK',
    provider: 'edge-azure',
    description: 'Technical Lead. Dry, analytical, and measured British accent.',
  },
];

const SELECTED_VOICE_KEY = 'skillissue_voice_id';

export function getSelectedVoice(): string {
  if (typeof window === 'undefined') return 'aws-polly-matthew';
  return localStorage.getItem(SELECTED_VOICE_KEY) || 'aws-polly-matthew';
}

export function setSelectedVoice(voiceId: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(SELECTED_VOICE_KEY, voiceId);
}

// Global active audio playback reference
let activeAudio: HTMLAudioElement | null = null;
let activeAudioUrl: string | null = null;

export class SpeechHandler {
  public isSupported: boolean = false;
  private isListening: boolean = false;
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private audioChunks: Blob[] = [];
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private animFrameId: number | null = null;

  private static globalAudioContext: AudioContext | null = null;

  constructor(
    private onResult: (text: string, isFinal: boolean) => void,
    private onError: (err: string) => void,
    private onStateChange: (listening: boolean) => void,
    private onAudioLevel?: (level: number) => void
  ) {
    if (typeof window !== 'undefined') {
      const hasMedia = !!(
        navigator.mediaDevices &&
        typeof navigator.mediaDevices.getUserMedia === 'function' &&
        window.MediaRecorder
      );
      this.isSupported = hasMedia;
    }
  }

  // Pre-activates browser audio subsystem on user gesture so auto-speak plays seamlessly
  public static unlockAudioContext() {
    if (typeof window === 'undefined') return;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      if (!SpeechHandler.globalAudioContext || SpeechHandler.globalAudioContext.state === 'closed') {
        SpeechHandler.globalAudioContext = new AudioCtx();
      }
      if (SpeechHandler.globalAudioContext.state === 'suspended') {
        SpeechHandler.globalAudioContext.resume();
      }
      // Warm up an inaudible 1-sample buffer to satisfy browser autoplay policies
      const buffer = SpeechHandler.globalAudioContext.createBuffer(1, 1, 22050);
      const source = SpeechHandler.globalAudioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(SpeechHandler.globalAudioContext.destination);
      source.start(0);
    } catch (e) {
      console.warn('AudioContext pre-activation notice:', e);
    }
  }

  async start() {
    if (this.isListening) return;

    // Pre-activate audio context on user gesture
    SpeechHandler.unlockAudioContext();
    this.audioChunks = [];

    // Initialize Microphone Audio Stream & Audio Level Visualizer
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: 16000,
          },
        });
        this.audioStream = stream;
        this.startAudioMeter(stream);

        let mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported('audio/webm')) {
          if (MediaRecorder.isTypeSupported('audio/mp4')) {
            mimeType = 'audio/mp4';
          } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
            mimeType = 'audio/ogg';
          } else {
            mimeType = '';
          }
        }

        const recorder = mimeType
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream);
        this.mediaRecorder = recorder;

        recorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };

        recorder.onstop = async () => {
          this.stopAudioMeter();
          if (this.audioChunks.length === 0) {
            return;
          }

          const mime = this.mediaRecorder?.mimeType || 'audio/webm';
          const audioBlob = new Blob(this.audioChunks, { type: mime });
          this.audioChunks = [];

          try {
            const formData = new FormData();
            const ext = mime.includes('mp4') ? 'm4a' : mime.includes('ogg') ? 'ogg' : 'webm';
            formData.append('audio', audioBlob, `recording.${ext}`);

            // Send clean audio to server-side Faster-Whisper / AWS Transcribe
            const res = await api.post<{ text: string }>('/audio/stt', formData);
            if (res.text && res.text.trim()) {
              this.onResult(res.text.trim(), true);
            }
          } catch (err: any) {
            console.warn('Server STT notice:', err);
            if (this.onError) this.onError(err.message || 'Speech recognition failed');
          }
        };

        recorder.start(250);
        this.isListening = true;
        this.onStateChange(true);
      }
    } catch (micErr: any) {
      console.warn('Microphone permission notice:', micErr);
      if (this.onError) this.onError(micErr.message || 'Microphone access denied');
    }
  }

  stop() {
    this.isListening = false;
    this.onStateChange(false);

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        this.mediaRecorder.stop();
      } catch (e) {
        console.warn('MediaRecorder stop notice:', e);
      }
    }

    if (this.audioStream) {
      this.audioStream.getTracks().forEach((track) => track.stop());
      this.audioStream = null;
    }

    this.stopAudioMeter();
  }

  private startAudioMeter(stream: MediaStream) {
    if (!this.onAudioLevel) return;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      this.audioContext = new AudioCtx();
      const source = this.audioContext.createMediaStreamSource(stream);
      const analyser = this.audioContext.createAnalyser();
      analyser.fftSize = 64;
      analyser.smoothingTimeConstant = 0.5;
      source.connect(analyser);
      this.analyser = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const update = () => {
        if (!this.analyser) return;
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(1.0, avg / 128.0);
        if (this.onAudioLevel) {
          this.onAudioLevel(normalized);
        }
        this.animFrameId = requestAnimationFrame(update);
      };
      this.animFrameId = requestAnimationFrame(update);
    } catch (e) {
      console.warn('Audio meter initialization notice:', e);
    }
  }

  private stopAudioMeter() {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close();
      } catch (e) {}
      this.audioContext = null;
    }
    this.analyser = null;
    if (this.onAudioLevel) {
      this.onAudioLevel(0);
    }
  }

  // --- Studio Neural TTS Implementation with Auto-Play by Default ---

  static async speak(text: string, onEnd?: () => void, voice?: string) {
    SpeechHandler.stopSpeaking();
    SpeechHandler.unlockAudioContext();

    const selectedVoice = voice || getSelectedVoice();

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('skillissue_token') : null;
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch('/api/v1/audio/tts', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          text,
          voice: selectedVoice,
        }),
      });

      if (!res.ok) {
        throw new Error(`TTS server returned status ${res.status}`);
      }

      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      activeAudioUrl = objectUrl;

      const audio = new Audio(objectUrl);
      activeAudio = audio;

      audio.onended = () => {
        if (activeAudioUrl) {
          URL.revokeObjectURL(activeAudioUrl);
          activeAudioUrl = null;
        }
        activeAudio = null;
        if (onEnd) onEnd();
      };

      audio.onerror = (e) => {
        console.warn('HTML5 Audio playback error:', e);
        if (activeAudioUrl) {
          URL.revokeObjectURL(activeAudioUrl);
          activeAudioUrl = null;
        }
        activeAudio = null;
        if (onEnd) onEnd();
      };

      try {
        await audio.play();
      } catch (playErr: any) {
        // If browser blocks unprompted autoplay before initial gesture, attach auto-resume on first interaction
        if (playErr.name === 'NotAllowedError') {
          const resumeOnFirstTouch = () => {
            audio.play().catch(() => {});
            document.removeEventListener('click', resumeOnFirstTouch);
            document.removeEventListener('keydown', resumeOnFirstTouch);
          };
          document.addEventListener('click', resumeOnFirstTouch, { once: true });
          document.addEventListener('keydown', resumeOnFirstTouch, { once: true });
        } else {
          throw playErr;
        }
      }
    } catch (err) {
      console.warn('Cloud Neural TTS failed, fallback to native SpeechSynthesis:', err);

      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.lang = 'en-US';
        if (onEnd) {
          utterance.onend = onEnd;
          utterance.onerror = () => onEnd();
        }
        window.speechSynthesis.speak(utterance);
      } else {
        if (onEnd) onEnd();
      }
    }
  }

  static stopSpeaking() {
    if (activeAudio) {
      try {
        activeAudio.pause();
        activeAudio.currentTime = 0;
      } catch (e) {}
      activeAudio = null;
    }
    if (activeAudioUrl) {
      try {
        URL.revokeObjectURL(activeAudioUrl);
      } catch (e) {}
      activeAudioUrl = null;
    }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  static async fetchVoices(): Promise<VoiceOption[]> {
    try {
      const res = await api.get<{ voices: VoiceOption[]; default_voice: string }>('/audio/voices');
      return res.voices || DEFAULT_VOICES;
    } catch (e) {
      return DEFAULT_VOICES;
    }
  }
}
