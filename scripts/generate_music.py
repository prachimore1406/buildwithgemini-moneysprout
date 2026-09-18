import math
import numpy as np
import wave
import os
import imageio_ffmpeg

def generate_upbeat_track(output_wav, duration_sec=65.0, sample_rate=44100):
    bpm = 124.0
    beat_sec = 60.0 / bpm
    eighth_sec = beat_sec / 2.0
    total_samples = int(sample_rate * duration_sec)
    
    audio = np.zeros(total_samples, dtype=np.float32)
    
    # Frequencies (Hz)
    notes = {
        'C3': 130.81, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00, 'A3': 220.00, 'B3': 246.94,
        'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00,
        'A4': 440.00, 'B4': 493.88, 'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'G5': 783.99
    }
    
    # 4-bar Upbeat Progression: C -> G -> Am -> F
    progressions = [
        ['C4', 'E4', 'G4', 'C5', 'E5', 'G4', 'E4', 'C5'], # C major arpeggio
        ['G3', 'D4', 'G4', 'B4', 'D5', 'G4', 'D4', 'B4'], # G major arpeggio
        ['A3', 'C4', 'E4', 'A4', 'C5', 'E4', 'C4', 'A4'], # A minor arpeggio
        ['F3', 'A3', 'C4', 'F4', 'A4', 'C4', 'A3', 'F4']  # F major arpeggio
    ]
    
    bass_notes = ['C3', 'G3', 'A3', 'F3']
    
    num_eighths = int(duration_sec / eighth_sec) + 1
    
    for i in range(num_eighths):
        start_idx = int(i * eighth_sec * sample_rate)
        if start_idx >= total_samples:
            break
            
        bar_idx = (i // 8) % len(progressions)
        note_in_bar = i % 8
        
        # 1. Melodic Arpeggio Synth Note
        note_name = progressions[bar_idx][note_in_bar]
        freq = notes[note_name]
        note_duration = int(eighth_sec * 0.9 * sample_rate)
        end_idx = min(start_idx + note_duration, total_samples)
        
        t = np.arange(end_idx - start_idx) / sample_rate
        # Upbeat marimba/pluck envelope (fast decay)
        envelope = np.exp(-12.0 * t)
        wave_sample = (0.5 * np.sin(2 * np.pi * freq * t) + 
                       0.3 * np.sin(2 * np.pi * freq * 2 * t) + 
                       0.2 * np.sin(2 * np.pi * freq * 3 * t)) * envelope
        audio[start_idx:end_idx] += wave_sample * 0.25
        
        # 2. Bassline Note (on beat 1 and beat 3)
        if note_in_bar % 4 == 0:
            bass_freq = notes[bass_notes[bar_idx]]
            bass_duration = int(beat_sec * 0.85 * sample_rate)
            b_end = min(start_idx + bass_duration, total_samples)
            tb = np.arange(b_end - start_idx) / sample_rate
            bass_env = np.exp(-4.0 * tb)
            bass_wave = 0.6 * np.sin(2 * np.pi * bass_freq * tb) * bass_env
            audio[start_idx:b_end] += bass_wave * 0.35
            
        # 3. Upbeat Percussion (Kick on beat 1, 3; Snare on beat 2, 4; Hi-hat on 8ths)
        # Hi-hat tick
        hh_dur = int(0.04 * sample_rate)
        hh_end = min(start_idx + hh_dur, total_samples)
        hh_noise = (np.random.rand(hh_end - start_idx) * 2 - 1) * np.exp(-40.0 * np.arange(hh_end - start_idx)/sample_rate)
        audio[start_idx:hh_end] += hh_noise * 0.06
        
        # Snare on beats 2 & 4
        if note_in_bar in [2, 6]:
            sn_dur = int(0.12 * sample_rate)
            sn_end = min(start_idx + sn_dur, total_samples)
            ts = np.arange(sn_end - start_idx) / sample_rate
            sn_noise = (np.random.rand(sn_end - start_idx) * 2 - 1) * np.exp(-20.0 * ts)
            sn_tone = np.sin(2 * np.pi * 180 * ts) * np.exp(-15.0 * ts)
            audio[start_idx:sn_end] += (sn_noise * 0.2 + sn_tone * 0.25) * 0.3
            
    # Normalize audio output
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = (audio / max_val) * 0.8
        
    audio_int16 = (audio * 32767).astype(np.int16)
    
    with wave.open(output_wav, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
        
    print(f"Upbeat music track generated at: {output_wav}")
    return output_wav

if __name__ == "__main__":
    generate_upbeat_track("/config/.gemini/antigravity/brain/8b827626-7e91-43fe-a673-6c2b6abd6a85/upbeat_music.wav", 65.0)
