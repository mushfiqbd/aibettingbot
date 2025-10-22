import os
import logging
import tempfile
from gtts import gTTS

try:
    from elevenlabs import Client, VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

from config import VOICE_ENABLED, VOICE_ENGINE, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID

logger = logging.getLogger(__name__)


class VoiceHandler:
    def __init__(self):
        self.voice_enabled = VOICE_ENABLED
        self.voice_engine = VOICE_ENGINE
        self.temp_dir = tempfile.gettempdir()
        
        # Initialize ElevenLabs if available
        if self.voice_engine == "elevenlabs" and ELEVENLABS_AVAILABLE:
            try:
                self.elevenlabs_client = Client(api_key=ELEVENLABS_API_KEY)
                self.elevenlabs_available = True
                logger.info("✅ ElevenLabs initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ ElevenLabs initialization failed: {e}. Falling back to gTTS")
                self.elevenlabs_available = False
        else:
            self.elevenlabs_available = False

    def generate_voice(self, text, lang="en"):
        """
        Generate voice from text using ElevenLabs or gTTS
        Returns the file path of the generated audio
        """
        if not self.voice_enabled:
            return None
        
        try:
            # Try ElevenLabs first if configured
            if self.voice_engine == "elevenlabs" and self.elevenlabs_available:
                return self._generate_elevenlabs_voice(text)
            else:
                # Fallback to gTTS
                return self._generate_gtts_voice(text, lang)
        except Exception as e:
            logger.error(f"Error generating voice: {e}")
            return None

    def _generate_elevenlabs_voice(self, text):
        """
        Generate voice using ElevenLabs API
        """
        try:
            filename = os.path.join(self.temp_dir, f"elevenlabs_voice_{hash(text)}.mp3")
            
            # Generate audio using ElevenLabs with proper voice_id
            audio = self.elevenlabs_client.generate(
                text=text,
                voice=ELEVENLABS_VOICE_ID,  # Pass voice ID directly
                model=ELEVENLABS_MODEL_ID,
                voice_settings=VoiceSettings(
                    stability=0.71,
                    similarity_boost=0.75
                )
            )
            
            # Save the audio file
            with open(filename, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            
            logger.info(f"✅ ElevenLabs voice generated: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ ElevenLabs error: {e}. Falling back to gTTS")
            return self._generate_gtts_voice(text, lang="en")  # Use English for fallback

    def _generate_gtts_voice(self, text, lang="en"):
        """
        Generate voice using gTTS (fallback)
        """
        try:
            filename = os.path.join(self.temp_dir, f"gtts_voice_{hash(text)}.mp3")
            
            # Generate audio using gTTS
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(filename)
            
            logger.info(f"✅ gTTS voice generated: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error generating gTTS voice: {e}")
            return None

    def get_voice_message(self, text, lang="en"):
        """
        Get voice message for text
        """
        if not self.voice_enabled:
            return None
        
        try:
            voice_file = self.generate_voice(text, lang)
            if voice_file and os.path.exists(voice_file):
                return open(voice_file, 'rb')
            return None
        except Exception as e:
            logger.error(f"Error getting voice message: {e}")
            return None

    def create_welcome_voice(self):
        """
        Create welcome voice message in English
        """
        text = "Welcome! I am your betting bot. How can I help you today?"
        return self.generate_voice(text, lang="en")

    def create_bet_confirmation_voice(self, team, odds, amount):
        """
        Create bet confirmation voice in English with better formatting
        """
        # Format odds as positive or negative
        odds_str = f"{odds:+.0f}"
        
        # Create a natural sounding message
        text = f"Congratulations! Your bet has been successfully placed. You have bet {amount} dollars on {team} at odds of {odds_str}. Good luck!"
        
        return self.generate_voice(text, lang="en")

    def create_balance_voice(self, balance):
        """
        Create balance check voice in English
        """
        text = f"Your current balance is {balance} dollars"
        return self.generate_voice(text, lang="en")

    def create_error_voice(self, message):
        """
        Create error message voice in English
        """
        text = f"Error: {message}"
        return self.generate_voice(text, lang="en")

    def create_match_voice(self, home_team, away_team):
        """
        Create match announcement voice in English
        """
        text = f"Match: {home_team} versus {away_team}. Select the match to place your bet."
        return self.generate_voice(text, lang="en")

    def cleanup_old_files(self):
        """
        Clean up old voice files
        """
        try:
            for file in os.listdir(self.temp_dir):
                if file.startswith("elevenlabs_voice_") or file.startswith("gtts_voice_") or file.startswith("bot_voice_"):
                    file_path = os.path.join(self.temp_dir, file)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
            logger.info("✅ Old voice files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up voice files: {e}")

    def get_voice_engine_status(self):
        """
        Get current voice engine status
        """
        if self.voice_engine == "elevenlabs":
            if self.elevenlabs_available:
                return "🎙️ ElevenLabs (Active)"
            else:
                return "🎙️ ElevenLabs (Unavailable - Using gTTS)"
        else:
            return "🎙️ gTTS (Active)"


# Initialize voice handler
voice_handler = VoiceHandler()
