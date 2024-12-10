import json
import re
from typing import Dict, List, Tuple

from langchain.tools import BaseTool


class MessageParser:
    """Helper class to handle message parsing and tool name normalization."""
    
    def __init__(self, tools: List[BaseTool]):
        self.tools = tools
        self._tool_names = {t.name.lower().strip(): t.name for t in tools}
        
        # Extended patterns for LLM-related terms
        self._llm_patterns = [
            "gpt", "llm", "openai", "language", "model", "ai", "assistant",
            "chatbot", "chat", "completion", "response", "answer", "claude",
            "anthropic", "gemini", "bard", "davinci", "turbo"
        ]

    def normalize_action(self, action: str) -> str:
        """Normalize action name and validate it exists in available tools."""
        # Clean and normalize the action name
        normalized = action.lower().strip().replace(" ", "-")
        
        # Check if it's a valid tool name
        if normalized in self._tool_names:
            return self._tool_names[normalized]
            
        # If not found, try to recover from common patterns
        action_lower = action.lower()
        if any(x in action_lower for x in self._llm_patterns):
            return "speak"  # Default to speak for LLM-related actions
            
        raise ValueError(f"Unknown action: {action}. Valid actions are: {', '.join(self._tool_names.values())}")

    def extract_message(self, text: str) -> dict:
        """Extract recipient and message from text with multiple fallback strategies."""
        # Try JSON first
        if text.strip().startswith('{'):
            try:
                data = json.loads(text)
                if isinstance(data, dict) and 'recipient' in data and 'message' in data:
                    return {
                        'recipient': data['recipient'].strip(),
                        'message': data['message'].strip()
                    }
            except:
                pass

        # Try newline split
        parts = text.strip().split('\n', 1)
        if len(parts) == 2:
            return {
                'recipient': parts[0].strip(),
                'message': parts[1].strip()
            }

        # Try to find recipient in common patterns
        patterns = [
            # Standard format patterns
            r"(?:to|recipient|target):\s*([^\n]+)\s*(?:message|content)?:\s*(.*)",
            r"([^:]+):\s*(.*)",
            
            # LLM-style output patterns
            r"(?:User|Human|Assistant|AI):\s*([^\n]+)\s*(?:Message|Response):\s*(.*)",
            r"(?:Input|Output|Query|Answer):\s*([^\n]+)\s*(?:Content|Text):\s*(.*)",
            
            # Conversation-style patterns
            r"(?:Tell|Ask|Inform|Notify)\s+([^\n]+)\s+(?:that|about|regarding):\s*(.*)",
            r"(?:Send|Message|Write\s+to)\s+([^\n]+):\s*(.*)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return {
                    'recipient': match.group(1).strip(),
                    'message': match.group(2).strip()
                }

        # Last resort: look for name at start
        words = text.strip().split()
        if words:
            return {
                'recipient': words[0],
                'message': ' '.join(words[1:]) if len(words) > 1 else text
            }

        raise ValueError("Could not extract recipient and message from input")

    def extract_action_input(self, text: str) -> Tuple[str, str]:
        """Extract action and input from LLM output."""
        # Standard action/input pattern
        regex = r"Action\s*\d*\s*:(.*?)(?:Action\s*\d*\s*Input\s*\d*\s*:[\s]*)(.*?)(?=\n\s*(?:Observation|Action|$))"
        match = re.search(regex, text, re.DOTALL)
        
        if not match:
            # Try LLM-style output patterns
            llm_patterns = [
                # Function call style
                r"(?:Function|Method|Tool)\s*Call:\s*(.*?)\s*(?:Parameters|Args|Input):\s*(.*?)(?=\n|$)",
                # API style
                r"(?:API|Endpoint):\s*(.*?)\s*(?:Body|Payload|Data):\s*(.*?)(?=\n|$)",
                # Natural language style
                r"(?:I will|Let me|I'll)\s*(.*?)\s*with(?:input|parameters|arguments)?:\s*(.*?)(?=\n|$)",
            ]
            
            for pattern in llm_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1).strip(), match.group(2).strip()
            
            # If no patterns match, try to find any message-like content
            text_lower = text.lower()
            for name in ["tata", "gaia", "everyone"]:
                if name in text_lower:
                    return "speak", text

            raise ValueError("Could not extract action and input from text")
            
        return match.group(1).strip(), match.group(2).strip()
