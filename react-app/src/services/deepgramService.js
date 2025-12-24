import config from '../../config';

/**
 * Convert WebM audio to WAV format for better Deepgram compatibility
 */
const convertToWav = async (audioBlob) => {
  return new Promise((resolve, reject) => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const fileReader = new FileReader();

    fileReader.onload = async (e) => {
      try {
        const arrayBuffer = e.target.result;
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        // Convert to WAV
        const wavBuffer = audioBufferToWav(audioBuffer);
        const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
        resolve(wavBlob);
      } catch (error) {
        reject(error);
      }
    };

    fileReader.onerror = reject;
    fileReader.readAsArrayBuffer(audioBlob);
  });
};

/**
 * Convert AudioBuffer to WAV format
 */
const audioBufferToWav = (audioBuffer) => {
  const numChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;

  const bytesPerSample = bitDepth / 8;
  const blockAlign = numChannels * bytesPerSample;

  const data = [];
  for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
    data.push(audioBuffer.getChannelData(i));
  }

  const interleaved = interleave(data);
  const dataLength = interleaved.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);

  // Write WAV header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, format, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitDepth, true);
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Write audio data
  floatTo16BitPCM(view, 44, interleaved);

  return buffer;
};

const interleave = (channelData) => {
  const length = channelData[0].length;
  const numChannels = channelData.length;
  const result = new Float32Array(length * numChannels);

  let offset = 0;
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numChannels; channel++) {
      result[offset++] = channelData[channel][i];
    }
  }
  return result;
};

const writeString = (view, offset, string) => {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
};

const floatTo16BitPCM = (view, offset, input) => {
  for (let i = 0; i < input.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
};

/**
 * Transcribe audio file to text using Deepgram STT
 */
export const transcribeAudio = async (audioBlob) => {
  try {
    console.log('[Deepgram STT] Starting transcription');
    console.log('[Deepgram STT] Original audio type:', audioBlob.type, 'size:', audioBlob.size);

    if (!config.DEEPGRAM_API_KEY) {
      throw new Error('Deepgram API key is not configured. Please add DEEPGRAM_API_KEY to your .env file.');
    }

    // Send audio directly without conversion - Deepgram supports WebM
    console.log('[Deepgram STT] Sending audio to Deepgram...');

    const formData = new FormData();
    // Send as WebM with Opus codec - Deepgram supports this
    formData.append('file', audioBlob, 'recording.webm');

    const response = await fetch(
      `https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&encoding=opus`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Token ${config.DEEPGRAM_API_KEY}`,
        },
        body: formData,
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Deepgram STT failed: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const transcript = data.results.channels[0].alternatives[0].transcript;

    console.log('[Deepgram STT] Transcription successful:', transcript);
    return transcript;
  } catch (error) {
    console.error('[Deepgram STT] Error:', error);
    throw new Error(`Failed to transcribe audio: ${error.message}`);
  }
};

/**
 * Convert text to speech using Deepgram TTS (optional for future use)
 */
export const textToSpeech = async (text, voice = 'aura-asteria-en') => {
  try {
    console.log('[Deepgram TTS] Converting text to speech:', text.substring(0, 50) + '...');

    const response = await fetch(
      `https://api.deepgram.com/v1/speak?model=${voice}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Token ${config.DEEPGRAM_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Deepgram TTS failed: ${response.status} - ${errorText}`);
    }

    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);

    console.log('[Deepgram TTS] Audio generated successfully');
    return audioUrl;
  } catch (error) {
    console.error('[Deepgram TTS] Error:', error);
    throw new Error(`Failed to convert text to speech: ${error.message}`);
  }
};
