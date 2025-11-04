import os
import tempfile
import base64
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

from openai import OpenAI
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
from config import settings

class AudioProcessor:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
    
    def process_audio_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Process audio file: convert format and transcribe speech to text

        Args:
            file_path: Audio file path
            filename: Original filename

        Returns:
            Dictionary containing transcription results
        """
        try:
            logger.info(f"Starting audio file processing: {filename}")

            # Detect file type
            file_ext = Path(filename).suffix.lower()
            logger.info(f"File format: {file_ext}")

            # Convert to supported audio format
            audio_path = self._convert_to_audio(file_path, file_ext)

            # Speech to text
            transcription = self._transcribe_audio(audio_path)

            # Clean up temporary file
            if audio_path != file_path:
                os.unlink(audio_path)

            result = {
                "filename": filename,
                "transcription": transcription,
                "duration": self._get_audio_duration(file_path, file_ext),
                "format": file_ext
            }

            logger.info(f"✅ Audio processing complete: {len(transcription)} characters")
            return result

        except Exception as e:
            logger.error(f"❌ Audio processing failed: {e}")
            raise Exception(f"Audio processing failed: {str(e)}")
    
    def _convert_to_audio(self, file_path: str, file_ext: str) -> str:
        """
        Convert video file to audio file

        Args:
            file_path: Source file path
            file_ext: File extension

        Returns:
            Audio file path
        """
        # If video file, extract audio
        if file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
            logger.info("🎬 Detected video file, extracting audio...")

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_audio_path = temp_file.name

            # Use moviepy to extract audio
            video = VideoFileClip(file_path)
            audio = video.audio
            audio.write_audiofile(temp_audio_path, verbose=False, logger=None)
            audio.close()
            video.close()

            logger.info(f"✅ Audio extraction complete: {temp_audio_path}")
            return temp_audio_path

        # If already audio file, check if format conversion is needed
        elif file_ext in ['.mp3', '.wav', '.flac', '.m4a', '.ogg']:
            # OpenAI Whisper supports these formats, return directly
            return file_path

        else:
            # Try converting with pydub
            logger.info(f"🔄 Converting audio format: {file_ext}")

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_audio_path = temp_file.name

            audio = AudioSegment.from_file(file_path)
            audio.export(temp_audio_path, format="wav")

            logger.info(f"✅ Format conversion complete: {temp_audio_path}")
            return temp_audio_path
    
    def _transcribe_audio(self, audio_path: str) -> str:
        """
        Use OpenAI Whisper for speech-to-text transcription

        Args:
            audio_path: Audio file path

        Returns:
            Transcription text
        """
        logger.info("🗣️ Starting speech-to-text transcription...")

        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        transcription = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()
        logger.info(f"📝 Transcription result length: {len(transcription)} characters")

        return transcription

    def _get_audio_duration(self, file_path: str, file_ext: str) -> float:
        """
        Get audio duration (seconds)

        Args:
            file_path: File path
            file_ext: File extension

        Returns:
            Duration (seconds)
        """
        try:
            if file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                # Video file
                video = VideoFileClip(file_path)
                duration = video.duration
                video.close()
                return duration
            else:
                # Audio file
                audio = AudioSegment.from_file(file_path)
                return len(audio) / 1000.0  # Convert to seconds
        except Exception as e:
            logger.warning(f"⚠️ Unable to get audio duration: {e}")
            return 0.0

    def process_audio_base64(self, base64_data: str, filename: str) -> Dict[str, Any]:
        """
        Process base64-encoded audio data

        Args:
            base64_data: base64-encoded audio data
            filename: Filename

        Returns:
            Dictionary containing transcription results
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
            # Decode base64 data
            audio_data = base64.b64decode(base64_data)
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        try:
            # Process audio file
            result = self.process_audio_file(temp_file_path, filename)
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path) 