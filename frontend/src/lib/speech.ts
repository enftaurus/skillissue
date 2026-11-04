// Cross-Browser Cloud Neural Speech Engine
// Studio-quality Text-to-Speech (HTML5 Audio streaming via /api/v1/audio/tts)
// Cross-Browser Speech-to-Text (MediaRecorder via /api/v1/audio/stt)
// Flawless performance in Firefox, Chrome, Safari, and Edge.

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
    id: 'en-US-ChristopherNeural',
    name: 'Christopher (US Male)',
    gender: 'Male',
    accent: 'US',
    provider: 'edge-azure',
    description: 'Senior Staff Engineer & Hiring Manager. Authoritative, direct, crisp.',
  },
  {
    id: 'en-US-JennyNeural',
    name: 'Jenny (US Female)',
    gender: 'Female',
    accent: 'US',
    provider: 'edge-azure',
    description: 'Lead Systems Architect. Clear, precise, articulate.',
  },
  {
    id: 'en-IN-NeerjaNeural',
    name: 'Neerja (India Female)',
    gender: 'Female',
    accent: 'India',
    provider: 'edge-azure',
    description: 'Principal Systems Engineer. Authentic Indian English cadence and clarity.',
  },
  {
    id: 'en-IN-PrabhatNeural',
    name: 'Prabhat (India Male)',
    gender: 'Male',
    accent: 'India',
    provider: 'edge-azure',
    description: 'Senior Technical Lead. Natural Indian English rhythm, methodical and sharp.',
  },
  {
    id: 'en-GB-RyanNeural',
    name: 'Ryan (UK Male)',
    gender: 'Male',
    accent: 'UK',
    provider: 'edge-azure',
    description: 'Technical Lead. Dry, analytical, and measured British accent.',
  },
];

const SELECTED_VOICE_KEY = 'skillissue_voice_id';

export function getSelectedVoice(): string {
  if (typeof window === 'undefined') return 'en-US-ChristopherNeural';
  return localStorage.getItem(SELECTED_VOICE_KEY) || 'en-US-ChristopherNeural';
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
  private recognition: any = null;
  private hasNativeSpeechResult: boolean = false;

  constructor(
    private onResult: (text: string, isFinal: boolean) => void,
    private onError: (err: string) => void,
    private onStateChange: (listening: boolean) => void,
    private onAudioLevel?: (level: number) => void
  ) {
    if (typeof window !== 'undefined') {
      const hasSpeechRec = !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
      const hasMedia = !!(
        navigator.mediaDevices &&
        typeof navigator.mediaDevices.getUserMedia === 'function' &&
        window.MediaRecorder
      );
      this.isSupported = hasSpeechRec || hasMedia;
    }
  }

  async start() {
    if (this.isListening) return;

    this.hasNativeSpeechResult = false;
    this.audioChunks = [];

    // 1. Initialize Microphone Audio Stream & Audio Level Visualizer
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        this.audioStream = stream;
        this.startAudioMeter(stream);

        // Fallback recorder if Web Speech API isn't present
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
          // If native web speech already produced results, skip slow backend STT
          if (this.hasNativeSpeechResult || this.audioChunks.length === 0) {
            this.audioChunks = [];
            return;
          }

          const mime = this.mediaRecorder?.mimeType || 'audio/webm';
          const audioBlob = new Blob(this.audioChunks, { type: mime });
          this.audioChunks = [];

          try {
            const formData = new FormData();
            const ext = mime.includes('mp4') ? 'm4a' : mime.includes('ogg') ? 'ogg' : 'webm';
            formData.append('audio', audioBlob, `recording.${ext}`);

            const res = await api.post<{ text: string }>('/audio/stt', formData);
            if (res.text && res.text.trim()) {
              this.onResult(res.text.trim(), true);
            }
          } catch (err: any) {
            console.warn('Backend STT notice:', err);
          }
        };

        recorder.start(250);
      }
    } catch (micErr: any) {
      console.warn('Microphone permission notice:', micErr);
      if (this.onError) this.onError(micErr.message || 'Microphone access denied');
    }

    // 2. Initialize Native High-Accuracy Streaming Speech Recognition (Web Speech API)
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        const rec = new SpeechRec();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = navigator.language || 'en-US';
        rec.maxAlternatives = 1;

        rec.onresult = (event: any) => {
          let interimTranscript = '';
          let finalTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }

          if (finalTranscript.trim()) {
            this.hasNativeSpeechResult = true;
            this.onResult(finalTranscript.trim(), true);
          } else if (interimTranscript.trim()) {
            this.onResult(interimTranscript.trim(), false);
          }
        };

        rec.onerror = (e: any) => {
          if (e.error === 'no-speech') {
            // Normal silence; do not abort
            return;
          }
          console.warn('Native speech recognition notice:', e.error);
          if (this.onError) this.onError(e.error);
        };

        rec.onend = () => {
          // If still marked as listening, restart recognition (Chrome ends on pauses)
          if (this.isListening && this.recognition) {
            try {
              this.recognition.start();
            } catch (e) {}
          }
        };

        rec.start();
        this.recognition = rec;
      } catch (recErr) {
        console.warn('Web Speech API instantiation notice:', recErr);
      }
    }

    this.isListening = true;
    this.onStateChange(true);
  }

  stop() {
    this.isListening = false;
    this.onStateChange(false);

    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {}
      this.recognition = null;
    }

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

  // --- Cloud Neural TTS Implementation with Auto-Play Resilience ---

  static async speak(text: string, onEnd?: () => void, voice?: string) {
    SpeechHandler.stopSpeaking();

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
        // If browser blocks unprompted autoplay before user gesture, attach one-time resume handler
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
