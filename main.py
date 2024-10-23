import pyaudio
import wave
import boto3
import time
import requests  # Add this for fetching the transcription result

# Constants for recording
AUDIO_FORMAT = pyaudio.paInt16  # 16-bit resolution
CHANNELS = 1                   # 1 channel for mono recording
RATE = 44100                    # 44.1kHz sampling rate
CHUNK = 1024                    # 2^10 samples for buffer size
RECORD_SECONDS = 10             # Duration of recording in seconds
OUTPUT_FILENAME = "recorded_audio.wav"  # Output file name

# AWS configurations
bucket_name = "chic-coders-malineni"
s3_file_path = f"audio/{OUTPUT_FILENAME}"

# Initialize PyAudio for recording
audio = pyaudio.PyAudio()

# Start the audio recording stream
stream = audio.open(format=AUDIO_FORMAT, channels=CHANNELS,
                    rate=RATE, input=True, frames_per_buffer=CHUNK)
print("Recording audio...")

# Record audio
frames = []
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("Finished recording.")

# Stop and close the stream
stream.stop_stream()
stream.close()
audio.terminate()

# Save the recorded audio to a .wav file
wavefile = wave.open(OUTPUT_FILENAME, 'wb')
wavefile.setnchannels(CHANNELS)
wavefile.setsampwidth(audio.get_sample_size(AUDIO_FORMAT))
wavefile.setframerate(RATE)
wavefile.writeframes(b''.join(frames))
wavefile.close()

print(f"Audio saved as {OUTPUT_FILENAME}")

# Initialize Boto3 clients
s3 = boto3.client('s3')
transcribe = boto3.client('transcribe')
translate = boto3.client('translate')
polly = boto3.client('polly')

# Upload the audio file to S3
s3.upload_file(OUTPUT_FILENAME, bucket_name, s3_file_path)
print(f"File uploaded to S3: {s3_file_path}")

# Transcription job parameters
job_name = f"transcription-job-{int(time.time())}"
media_uri = f"s3://{bucket_name}/{s3_file_path}"

# Start the transcription job
transcribe.start_transcription_job(
    TranscriptionJobName=job_name,
    Media={'MediaFileUri': media_uri},
    MediaFormat='wav',
    LanguageCode='en-US'  # Adjust based on the input language
)

print("Transcription job started...")

# Poll for job completion
while True:
    status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
        break
    print(f"Transcription job status: {status['TranscriptionJob']['TranscriptionJobStatus']}")
    time.sleep(10)

# Once transcription is completed
if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
    transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
    print(f"Transcription completed. Transcript available at: {transcript_uri}")

    # Fetch the transcription result directly from the public URL (TranscriptFileUri)
    transcript_response = requests.get(transcript_uri)
    
    # Check if the response is successful
    if transcript_response.status_code == 200:
        transcript_text = transcript_response.json()['results']['transcripts'][0]['transcript']
        print(f"Transcribed text: {transcript_text}")

        # Translate the transcription
        translation = translate.translate_text(
            Text=transcript_text,
            SourceLanguageCode='en',  # Original language (change based on input)
            TargetLanguageCode='hi-IN'  # Target language (e.g., 'es' for Spanish)
        )
        
        translated_text = translation['TranslatedText']
        print(f"Translated text: {translated_text}")

        # Convert the translated text to speech using Polly
        polly_response = polly.synthesize_speech(
            Text=translated_text,
            OutputFormat='mp3',
            VoiceId='Aditi'  # Voice based on the target language, e.g., 'Lucia' for Spanish
        )

        # Save the generated speech to an MP3 file
        with open('translated_speech.mp3', 'wb') as audio_file:
            audio_file.write(polly_response['AudioStream'].read())

        print("Audio generated from translated text.")
    else:
        print(f"Failed to fetch transcript: {transcript_response.status_code}")
else:
    print("Transcription failed.")

import pygame

# Initialize pygame mixer
pygame.mixer.init()

# Load and play the audio file
pygame.mixer.music.load("translated_speech.mp3")
pygame.mixer.music.play()

# Keep the program running while the audio plays
while pygame.mixer.music.get_busy():
    pygame.time.Clock().tick(10)  # Check every 10ms
