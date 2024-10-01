import librosa
import resampy
from pathlib import Path
import soundfile as sf
from speechbrain.pretrained import VAD
import torch
import os
import numpy as np
import tensorflow as tf
from config import ivr_model_path, resampled_audio_path, vad_model_path

def vad_remove_silence_music(audio_, music_model_path):
    audio, sr = librosa.load(audio_, sr=None)
    audio_resampled = resampy.resample(audio, sr, 16000)
    filename = resampled_audio_path + f"{Path(audio_).stem}.wav"
    sf.write(filename, audio_resampled, samplerate=16000)

    vad = VAD.from_hparams(source=music_model_path, savedir=vad_model_path)
    boundaries = vad.get_speech_segments(filename, apply_energy_VAD=True, close_th=3.0)

    segments = vad.get_segments(boundaries, filename)
    try:
        concatenated_tensor = torch.cat(segments, dim=-1)
        vad_audio = concatenated_tensor.cpu().detach().numpy().tolist()[0]
    except:
        vad_audio = audio
    os.remove(filename)
    return vad_audio, 16000, boundaries

def __preprocess_audio(audio, sample_rate):
    # Perform feature extraction, e.g., using MFCC
    mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=20)
    # Normalize the features
    normalized_mfcc = (mfcc - np.mean(mfcc)) / np.std(mfcc)
    normalized_mfcc = np.mean(normalized_mfcc, axis=1)
    return normalized_mfcc
    
def ivr_removed_audios(audio, ivr_model_path):
    with tf.device('/CPU:0'):
        model = tf.keras.models.load_model(ivr_model_path)
    sample_rate = 16000
    try: audio, sr = librosa.load(audio)
    except: pass
    # Define segment duration and overlap
    segment_duration = 4  # Duration of each segment in seconds
    overlap = 0.5  # Overlap between segments as a fraction (e.g., 0.5 for 50% overlap)
    # Calculate segment hop length based on duration and overlap
    segment_hop = int(segment_duration * sample_rate * (1 - overlap))
    human_voice_segments = []
    # Preprocess and make predictions on each segment
    for i in range(0, len(audio), segment_hop):
        try:
            segment = audio[i:i + segment_hop]
            # Preprocess the segment (extract features)
            segment_features = __preprocess_audio(segment, sample_rate)
            # Reshape the segment features to match the expected input shape
            segment_features = np.reshape(segment_features, (1, -1))
            segment_features = np.expand_dims(segment_features, axis=1)
            # Make predictions using your trained model
            with tf.device('/CPU:0'):
                predictions = model.predict(segment_features, verbose=0)
            # Interpret the predictions (e.g., classify as machine voice or human voice)
            if predictions[0] <= 0.98:
                # Save segments with human voice
                human_voice_segments.append(segment)
        except:
            pass
    # Concatenate human voice segments into a single audio
    human_voice_audio = np.concatenate(human_voice_segments)
    return human_voice_audio, 16000

def remove_music(file_path, music_model_path, agent=False):
    try:
        audio, sr, speech_segments = vad_remove_silence_music(file_path, music_model_path)
        if not agent:
            with tf.device('/CPU:0'):
                ivr_removed_audio, sr = ivr_removed_audios(np.array(audio), ivr_model_path)
        else:
            ivr_removed_audio = audio
    except Exception as e:
        print(f"Error occurred during music removal: {e}")
        # Fallback values in case of an error
        audio, sr = librosa.load(file_path, sr=8000)
        ivr_removed_audio = resampy.resample(audio, sr, 16000)
        speech_segments = []  # Initialize to an empty list if there is an error
        duration = len(audio)/sr  # Set duration based on the audio loaded
    
    duration = len(ivr_removed_audio)/sr
    return ivr_removed_audio, speech_segments, duration
