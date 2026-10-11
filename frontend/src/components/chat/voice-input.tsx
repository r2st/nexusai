'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Mic, MicOff, Loader2, Volume2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// Web Speech API types (not available in all TypeScript configurations)
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

// Extend Window interface for Web Speech API
declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
  }
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  start: () => void;
  stop: () => void;
}

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  onInterimTranscript?: (text: string) => void;
  disabled?: boolean;
  language?: string;
  continuous?: boolean;
  className?: string;
}

type SpeechRecognitionType = typeof window.SpeechRecognition;

/**
 * Voice input component for speech-to-text.
 * 
 * Provides accessible voice input for users who prefer or need
 * to speak rather than type. Uses the Web Speech API.
 */
export function VoiceInput({
  onTranscript,
  onInterimTranscript,
  disabled,
  language = 'en-US',
  continuous = false,
  className,
}: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [interimText, setInterimText] = useState('');
  const [audioLevel, setAudioLevel] = useState(0);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  // Check for browser support
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = continuous;
    recognition.interimResults = true;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimText('');
      stopAudioVisualization();
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      if (interimTranscript) {
        setInterimText(interimTranscript);
        onInterimTranscript?.(interimTranscript);
      }

      if (finalTranscript) {
        onTranscript(finalTranscript.trim());
        setInterimText('');
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);

      switch (event.error) {
        case 'no-speech':
          toast.info('No speech detected. Try again.');
          break;
        case 'audio-capture':
          toast.error('No microphone found. Please check your settings.');
          break;
        case 'not-allowed':
          toast.error('Microphone access denied. Please enable it in settings.');
          break;
        default:
          toast.error('Voice input error. Please try again.');
      }
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
      stopAudioVisualization();
    };
  }, [language, continuous, onTranscript, onInterimTranscript]);

  // Audio visualization
  const startAudioVisualization = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      analyserRef.current.fftSize = 256;

      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);

      const updateLevel = () => {
        if (!analyserRef.current) return;
        
        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setAudioLevel(average / 255);
        
        animationRef.current = requestAnimationFrame(updateLevel);
      };

      updateLevel();
    } catch (error) {
      console.error('Error starting audio visualization:', error);
    }
  }, []);

  const stopAudioVisualization = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setAudioLevel(0);
  }, []);

  const toggleListening = useCallback(async () => {
    if (!recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
      stopAudioVisualization();
    } else {
      try {
        recognitionRef.current.start();
        await startAudioVisualization();
      } catch (error) {
        console.error('Error starting recognition:', error);
        toast.error('Could not start voice input');
      }
    }
  }, [isListening, startAudioVisualization, stopAudioVisualization]);

  if (!isSupported) {
    return (
      <Button
        variant="ghost"
        size="icon"
        disabled
        className={cn('h-9 w-9', className)}
        title="Voice input not supported in this browser"
        aria-label="Voice input not supported"
      >
        <MicOff className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </Button>
    );
  }

  return (
    <div className={cn('relative', className)}>
      {/* Audio level indicator */}
      {isListening && (
        <div
          className="absolute inset-0 rounded-full bg-primary/20 transition-transform"
          style={{
            transform: `scale(${1 + audioLevel * 0.5})`,
          }}
        />
      )}

      <Button
        variant={isListening ? 'default' : 'ghost'}
        size="icon"
        onClick={toggleListening}
        disabled={disabled}
        className={cn(
          'relative h-9 w-9 transition-all',
          isListening && 'bg-red-500 hover:bg-red-600 text-white'
        )}
        aria-label={isListening ? 'Stop listening' : 'Start voice input'}
        aria-pressed={isListening}
        title={isListening ? 'Click to stop' : 'Voice input'}
      >
        {isListening ? (
          <MicOff className="h-4 w-4 animate-pulse" aria-hidden="true" />
        ) : (
          <Mic className="h-4 w-4" aria-hidden="true" />
        )}
      </Button>

      {/* Interim transcript display */}
      {isListening && interimText && (
        <div
          className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 px-3 py-1.5 
                     rounded-lg bg-popover border shadow-md text-sm whitespace-nowrap
                     max-w-[200px] truncate"
          role="status"
          aria-live="polite"
        >
          <span className="text-muted-foreground">{interimText}</span>
        </div>
      )}
    </div>
  );
}

/**
 * Voice input button with tooltip
 */
export function VoiceInputButton({
  onTranscript,
  disabled,
  className,
}: {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <VoiceInput
      onTranscript={onTranscript}
      disabled={disabled}
      className={className}
    />
  );
}

// Web Speech API is accessed via window object, types declared above
export default VoiceInput;
