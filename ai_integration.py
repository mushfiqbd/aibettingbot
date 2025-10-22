import logging
from openai import OpenAI
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class AIAssistant:
    def __init__(self):
        self.ai_available = False
        self.client = None
        self.model = "gpt-4o-mini"
        self.conversation_history = {}
        
        # Try to initialize OpenAI client
        try:
            if OPENAI_API_KEY == "YOUR_OPENAI_KEY_HERE":
                logger.warning("⚠️ OpenAI API Key not configured. AI features will be disabled.")
                return
            
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.ai_available = True
            logger.info("✅ OpenAI client initialized successfully")
        except TypeError as e:
            logger.warning(f"⚠️ OpenAI initialization error (compatibility issue): {e}")
            logger.info("🔧 Installing compatible versions...")
            self.ai_available = False
        except Exception as e:
            logger.error(f"❌ Error initializing OpenAI: {e}")
            self.ai_available = False

    def get_bet_suggestion(self, match_data):
        """
        Get AI-powered bet suggestion for a match
        """
        if not self.ai_available:
            return self._get_default_suggestion(match_data)
        
        try:
            prompt = f"""
আপনি একজন স্মার্ট বেটিং এক্সপার্ট। নিম্নলিখিত ম্যাচের ডেটা বিশ্লেষণ করুন এবং একটি স্মার্ট বেটিং সাজেশন দিন:

ম্যাচ তথ্য:
- হোম টিম: {match_data.get('home_team')}
- অ্যাওয়ে টিম: {match_data.get('away_team')}
- শুরুর সময়: {match_data.get('commence_time')}
- অডস: {match_data.get('odds', {})}

আপনার সাজেশনে অন্তর্ভুক্ত করুন:
1. সবচেয়ে সম্ভাব্য ফলাফল
2. সুপারিশকৃত বেট এবং পরিমাণ
3. ঝুঁকি বিশ্লেষণ
4. বাংলায় সংক্ষিপ্ত ব্যাখ্যা

সর্বদা দায়িত্বশীল বেটিং প্রচার করুন এবং সতর্কতা দিন।
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "আপনি একজন সহায়ক বেটিং কনসালট্যান্ট যিনি দায়িত্বশীল বেটিং প্রচার করেন। সর্বদা বাংলায় উত্তর দিন।"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting bet suggestion: {e}")
            return self._get_default_suggestion(match_data)

    def _get_default_suggestion(self, match_data):
        """
        Get default suggestion when AI is unavailable
        """
        home = match_data.get('home_team', 'Unknown')
        away = match_data.get('away_team', 'Unknown')
        return f"""
⚠️ এআই পরামর্শ এখন উপলব্ধ নয়।

🏆 ম্যাচ: {home} বনাম {away}

💡 সাধারণ পরামর্শ:
• ছোট পরিমাণে বেট করুন
• শুধুমাত্র যা হারাতে পারবেন তা বেট করুন
• দীর্ঘমেয়াদী কৌশল অনুসরণ করুন

⚙️ টিপ: এআই পরামর্শ পেতে OPENAI_API_KEY সেট করুন
"""

    def get_response(self, user_id, user_message):
        """
        Get conversational response from AI
        """
        if not self.ai_available:
            return "আমি এখন এআই সেবা প্রদান করতে পারছি না। কিন্তু আপনি বেট করতে এবং ব্যালেন্স চেক করতে পারেন। আরো সাহায্যের জন্য /help দেখুন।"
        
        try:
            # Initialize conversation history for new users
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # Add user message to history
            self.conversation_history[user_id].append({
                "role": "user",
                "content": user_message
            })
            
            # Keep only last 10 messages for context
            if len(self.conversation_history[user_id]) > 10:
                self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "আপনি একটি বন্ধুত্বপূর্ণ বেটিং বট যা ব্যবহারকারীদের সাহায্য করে এবং দায়িত্বশীল বেটিং প্রচার করে। সর্বদা বাংলায় উত্তর দিন।"}
                ] + self.conversation_history[user_id],
                max_tokens=300,
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message.content
            
            # Add response to history
            self.conversation_history[user_id].append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return "আমি এখন উত্তর দিতে পারছি না। আবার চেষ্টা করুন।"

    def analyze_betting_pattern(self, user_stats):
        """
        Analyze user's betting pattern and provide insights
        """
        if not self.ai_available:
            return "এআই বিশ্লেষণ এখন উপলব্ধ নয়। পরে আবার চেষ্টা করুন।"
        
        try:
            prompt = f"""
এই ব্যবহারকারীর বেটিং প্যাটার্ন বিশ্লেষণ করুন এবং উন্নতির পরামর্শ দিন:

- মোট বেট: {user_stats.get('total_bet', 0)}
- মোট জয়: {user_stats.get('total_win', 0)}
- মোট ক্ষতি: {user_stats.get('total_loss', 0)}
- বর্তমান ব্যালেন্স: {user_stats.get('balance', 0)}

বাংলায় একটি সংক্ষিপ্ত বিশ্লেষণ এবং পরামর্শ দিন।
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "আপনি একজন বেটিং বিশ্লেষক যিনি দায়িত্বশীল গেমিং প্রচার করেন। সর্বদা বাংলায় উত্তর দিন।"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing betting pattern: {e}")
            return "প্যাটার্ন বিশ্লেষণ এখন উপলব্ধ নয়।"

    def clear_conversation_history(self, user_id):
        """
        Clear conversation history for a user
        """
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]


# Initialize AI assistant with error handling
try:
    ai_assistant = AIAssistant()
except Exception as e:
    logger.error(f"Failed to create AI assistant: {e}")
    ai_assistant = AIAssistant()  # Create with fallback mode
