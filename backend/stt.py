# STUB: WhisperSTT in Phase 0 - Placeholder for Whisper model integration
# Phase 1 will replace this with actual Whisper model loading and transcription
# This stub allows integration testing of the STT interface without model dependencies


class WhisperSTT:
    """Stub Speech-to-Text provider using OpenAI's Whisper model.

    Phase 0: Returns hardcoded Spanish phrase for integration testing.
    Phase 1: Will integrate actual Whisper model for real transcription.
    """

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to the audio file to transcribe.

        Returns:
            Transcribed text. In Phase 0, returns hardcoded Spanish phrase.

        Note:
            Phase 0 stub - does not load actual Whisper model.
            Replace implementation in Phase 1.
        """
        # Stub return for Phase 0 integration testing
        return "hola cómo estás"
