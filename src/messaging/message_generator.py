"""
Message Generator - Creates personalized messages using LLM
Handles openers, responses, and goal-oriented conversations
"""

import os
import json
from typing import Dict, List, Optional
from enum import Enum
import openai
from anthropic import Anthropic
from loguru import logger
import random


class ConversationStage(Enum):
    OPENER = "opener"
    BUILD_RAPPORT = "build_rapport"
    DEEPEN_CONNECTION = "deepen_connection"
    SUGGEST_MOVE_OFF_APP = "suggest_move_off_app"
    GET_NUMBER = "get_number"
    SCHEDULE_DATE = "schedule_date"


class MessageGenerator:
    """Generates messages for dating app conversations"""
    
    def __init__(self, preferences_path: str = "config/preferences.json", llm_provider: str = "openai"):
        self.preferences = self._load_preferences(preferences_path)
        self.llm_provider = llm_provider
        self._setup_llm_client()
        self.conversation_templates = self._load_templates()
        
    def _load_preferences(self, path: str) -> Dict:
        """Load messaging preferences"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f).get('messaging', {})
        return {
            "style": "casual_witty",
            "goals": ["build_rapport", "get_number", "schedule_date"],
            "use_humor": True,
            "emoji_usage": "moderate"
        }
        
    def _setup_llm_client(self):
        """Initialize LLM client based on provider"""
        if self.llm_provider == "openai":
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model = "gpt-4"
        elif self.llm_provider == "anthropic":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = "claude-3-opus-20240229"
            
    def _load_templates(self) -> Dict:
        """Load conversation templates"""
        return {
            "openers": {
                "question": [
                    "I noticed you're into {interest}, what got you started with that?",
                    "Your photo at {location} looks amazing! How was that experience?",
                    "{bio_reference}... I'm curious, what's the story behind that?"
                ],
                "compliment": [
                    "Your {attribute} really caught my eye, and {bio_reference} makes you even more interesting!",
                    "Love that you're into {interest}! What's your favorite thing about it?"
                ],
                "humor": [
                    "So {bio_reference}... does that mean you're as {adjective} as you are {attribute}?",
                    "Important question: {interest} enthusiast by day, {other_interest} lover by night?"
                ]
            },
            "number_requests": [
                "This app is fun but I'd love to continue our conversation over text. What's your number?",
                "You seem really cool! Want to switch to texting? Here's my number: {user_number}",
                "I'm terrible at checking this app - mind if we move to text?"
            ],
            "date_suggestions": [
                "Would love to meet you in person! How about {activity} this {day}?",
                "I know a great {venue_type} that I think you'd love. Free this {day}?",
                "Since we both love {shared_interest}, want to {related_activity} this weekend?"
            ]
        }
        
    def generate_opener(self, profile_data: Dict) -> str:
        """Generate an opening message based on profile data"""
        logger.info("Generating opener message")
        
        prompt = self._build_opener_prompt(profile_data)
        
        if self.llm_provider == "openai":
            response = self._generate_openai(prompt)
        else:
            response = self._generate_anthropic(prompt)
            
        # Post-process to ensure appropriate length and style
        response = self._post_process_message(response, ConversationStage.OPENER)
        
        logger.debug(f"Generated opener: {response}")
        return response
        
    def generate_response(self, conversation_history: List[Dict], their_message: str) -> str:
        """Generate a contextual response"""
        stage = self._determine_conversation_stage(conversation_history)
        logger.info(f"Generating response for stage: {stage}")
        
        prompt = self._build_response_prompt(conversation_history, their_message, stage)
        
        if self.llm_provider == "openai":
            response = self._generate_openai(prompt)
        else:
            response = self._generate_anthropic(prompt)
            
        response = self._post_process_message(response, stage)
        
        logger.debug(f"Generated response: {response}")
        return response
        
    def _build_opener_prompt(self, profile_data: Dict) -> str:
        """Build prompt for opener generation"""
        style_desc = self._get_style_description()
        
        prompt = f"""Generate a dating app opening message with these requirements:

Profile Information:
- Name: {profile_data.get('name', 'Unknown')}
- Age: {profile_data.get('age', 'Unknown')}
- Bio: {profile_data.get('bio', 'No bio available')}
- Interests: {', '.join(profile_data.get('interests', []))}

Style Requirements:
{style_desc}

Message Requirements:
- Be {self.preferences.get('style', 'casual and friendly')}
- Reference something specific from their profile
- Keep it concise (1-2 sentences max)
- Make it engaging and unique (avoid generic openers)
- End with a question or conversation starter
{"- Include a subtle touch of humor" if self.preferences.get('use_humor') else ""}
{"- Use 1-2 emojis maximum" if self.preferences.get('emoji_usage') == 'moderate' else "- No emojis" if self.preferences.get('emoji_usage') == 'none' else ""}

Generate only the message text, nothing else."""

        return prompt
        
    def _build_response_prompt(self, conversation_history: List[Dict], their_message: str, stage: ConversationStage) -> str:
        """Build prompt for response generation"""
        style_desc = self._get_style_description()
        goal_desc = self._get_goal_description(stage)
        
        # Format conversation history
        history_text = ""
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            sender = "You" if msg['sender'] == 'user' else "Them"
            history_text += f"{sender}: {msg['text']}\n"
            
        prompt = f"""Generate a dating app response message with these requirements:

Conversation History:
{history_text}

Their Latest Message: {their_message}

Conversation Stage: {stage.value}
Goal: {goal_desc}

Style Requirements:
{style_desc}

Message Requirements:
- Respond naturally to their message
- {goal_desc}
- Be {self.preferences.get('style', 'casual and friendly')}
- Keep it concise (1-3 sentences max)
- Show genuine interest and personality
{"- Include appropriate humor if it fits" if self.preferences.get('use_humor') else ""}
{"- Use emojis sparingly" if self.preferences.get('emoji_usage') == 'moderate' else ""}

Generate only the message text, nothing else."""

        return prompt
        
    def _generate_openai(self, prompt: str) -> str:
        """Generate message using OpenAI"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a dating coach helping craft engaging, authentic messages."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._get_fallback_message()
            
    def _generate_anthropic(self, prompt: str) -> str:
        """Generate message using Anthropic Claude"""
        try:
            response = self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.8
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return self._get_fallback_message()
            
    def _determine_conversation_stage(self, conversation_history: List[Dict]) -> ConversationStage:
        """Determine current stage of conversation"""
        message_count = len(conversation_history)
        
        if message_count == 0:
            return ConversationStage.OPENER
        elif message_count < 5:
            return ConversationStage.BUILD_RAPPORT
        elif message_count < 10:
            return ConversationStage.DEEPEN_CONNECTION
        elif message_count < 15:
            # Check if we've asked for number yet
            for msg in conversation_history:
                if msg['sender'] == 'user' and any(word in msg['text'].lower() 
                    for word in ['number', 'text', 'phone', 'whatsapp']):
                    return ConversationStage.SCHEDULE_DATE
            return ConversationStage.SUGGEST_MOVE_OFF_APP
        else:
            return ConversationStage.GET_NUMBER
            
    def _get_style_description(self) -> str:
        """Get description of messaging style"""
        style_map = {
            "casual_witty": "Be casual, friendly, and occasionally witty without trying too hard",
            "formal": "Be polite, respectful, and somewhat formal",
            "funny": "Be humorous and playful while staying respectful",
            "flirty": "Be subtly flirty and charming without being inappropriate",
            "intellectual": "Be thoughtful and show intellectual curiosity"
        }
        return style_map.get(self.preferences.get('style', 'casual_witty'), 
                            "Be friendly and engaging")
                            
    def _get_goal_description(self, stage: ConversationStage) -> str:
        """Get description of conversation goal for current stage"""
        goal_map = {
            ConversationStage.BUILD_RAPPORT: "Build rapport and find common ground",
            ConversationStage.DEEPEN_CONNECTION: "Deepen the connection and show genuine interest",
            ConversationStage.SUGGEST_MOVE_OFF_APP: "Naturally suggest moving the conversation off the app",
            ConversationStage.GET_NUMBER: "Smoothly ask for their phone number",
            ConversationStage.SCHEDULE_DATE: "Suggest a specific date idea based on shared interests"
        }
        return goal_map.get(stage, "Keep the conversation engaging")
        
    def _post_process_message(self, message: str, stage: ConversationStage) -> str:
        """Post-process generated message"""
        # Remove any instruction text that might have leaked
        lines = message.split('\n')
        message = lines[0] if lines else message
        
        # Ensure appropriate length
        if stage == ConversationStage.OPENER:
            # Openers should be shorter
            sentences = message.split('. ')
            if len(sentences) > 2:
                message = '. '.join(sentences[:2]) + '.'
                
        # Add emoji if appropriate and missing
        if self.preferences.get('emoji_usage') == 'moderate' and '😀' not in message:
            if stage in [ConversationStage.OPENER, ConversationStage.BUILD_RAPPORT]:
                if random.random() < 0.3:  # 30% chance
                    emojis = ['😊', '😄', '🙂', '✨', '🎯', '💫']
                    message += f" {random.choice(emojis)}"
                    
        return message.strip()
        
    def _get_fallback_message(self) -> str:
        """Get fallback message if generation fails"""
        fallbacks = [
            "Hey! Your profile really caught my attention. How's your day going?",
            "Hi there! I'd love to know more about you. What's been the highlight of your week?",
            "Hey! You seem really interesting. What are you up to today?"
        ]
        return random.choice(fallbacks)
        
    def suggest_date(self, conversation_history: List[Dict], calendar_availability: List[Dict]) -> str:
        """Generate a date suggestion based on conversation and calendar"""
        # Extract shared interests from conversation
        shared_interests = self._extract_shared_interests(conversation_history)
        
        # Pick best time slot
        if calendar_availability:
            time_slot = calendar_availability[0]
            day = time_slot['day']
            time = time_slot['time']
        else:
            day = "this weekend"
            time = "afternoon"
            
        # Generate activity suggestion
        activity = self._suggest_activity(shared_interests)
        
        template = random.choice(self.conversation_templates['date_suggestions'])
        message = template.format(
            activity=activity,
            day=day,
            venue_type=self._get_venue_type(activity),
            shared_interest=shared_interests[0] if shared_interests else "good conversation"
        )
        
        return message
        
    def _extract_shared_interests(self, conversation_history: List[Dict]) -> List[str]:
        """Extract shared interests from conversation"""
        interests = []
        interest_keywords = self.preferences.get('interests', {}).get('preferred', [])
        
        for msg in conversation_history:
            for keyword in interest_keywords:
                if keyword.lower() in msg['text'].lower():
                    interests.append(keyword)
                    
        return list(set(interests))
        
    def _suggest_activity(self, shared_interests: List[str]) -> str:
        """Suggest date activity based on interests"""
        activity_map = {
            "coffee": "coffee at that new place downtown",
            "fitness": "a hike followed by smoothies",
            "wine": "wine tasting at that cozy bar",
            "art": "checking out the new gallery exhibition",
            "music": "live music at the jazz club",
            "foodie": "trying that new restaurant everyone's talking about"
        }
        
        for interest in shared_interests:
            if interest.lower() in activity_map:
                return activity_map[interest.lower()]
                
        # Default suggestion
        return "coffee or drinks"
        
    def _get_venue_type(self, activity: str) -> str:
        """Get venue type from activity"""
        if "coffee" in activity:
            return "coffee spot"
        elif "wine" in activity or "drinks" in activity:
            return "bar"
        elif "restaurant" in activity or "food" in activity:
            return "restaurant"
        else:
            return "place"