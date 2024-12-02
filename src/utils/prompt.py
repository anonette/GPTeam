import re
from enum import Enum

from langchain.schema import BaseMessage, SystemMessage
from pydantic import BaseModel


class Examples(Enum):
    PLAN_EXAMPLES = [""]


class PromptString(Enum):
    REFLECTION_QUESTIONS = "Here are a list of statements:\n{memory_descriptions}\n\nGiven only the information above, what are 3 most provocative questions we can answer about the subjects in the statements?\n\n{format_instructions}"

    REFLECTION_INSIGHTS = "\n{memory_strings}\nWhat 3 insights can you infer from the above statements?\nWhen referring to people, always specify their name.\n\n{format_instructions}"

    IMPORTANCE = "You are a memory importance AI. Given the character's profile and the memory description, rate the importance of the memory on a scale of 1 to 5, where 1 is purely mundane (e.g., repeating an action or speech, waiting) and 5 is extremely important (e.g., a new insight, new idea). Be sure to make your rating relative to the character's personality and concerns.\n\nExample #1:\nName: Jojo\nBio: Jojo is a professional ice-skater who loves specialty coffee. She hopes to compete in the olympics one day.\nMemory: Jojo sees a new coffee shop\n\n Your Response: '{{\"rating\": 3}}'\n\nExample #2:\nName: Skylar\nBio: Skylar is a product marketing manager. She works at a growth-stage tech company that makes autonomous cars. She loves cats.\nMemory: Skylar sees a new coffee shop\n\n Your Response: '{{\"rating\": 1}}'\n\nExample #3:\nName: Bob\nBio: Bob is a plumber living in the lower east side of New York City. He's been working as a plumber for 20 years. On the weekends he enjoys taking long walks with his wife. \nMemory: Bob's wife slaps him in the face.\n\n Your Response: '{{\"rating\": 5}}'\n\nExample #4:\nName: Thomas\nBio: Thomas is a police officer in Minneapolis. He joined the force only 6 months ago, and having a hard time at work because of his inexperience.\nMemory: Thomas accidentally spills his drink on a stranger\n\n Your Response: '{{\"rating\": 4}}'\n\nExample #5:\nName: Laura\nBio: Laura is a marketing specialist who works at a large tech company. She loves traveling and trying new foods. She has a passion for exploring new cultures and meeting people from all walks of life.\nMemory: Laura arrived at the meeting room\n\n Your Response: '{{\"rating\": 1}}'\n\n{format_instructions} Let's Begin! \n\n Name: {full_name}\nBio: {private_bio}\nMemory:{memory_description}\n\n"

    RECENT_ACTIIVITY = "Given the following memories, generate a short summary of what {full_name} has been doing lately, emphasizing any confrontational and dramatic interactions. Focus on conflicts, emotional reactions, and power struggles. Do not make up details that are not specified in the memories. For any conversations, be sure to mention if the conversations are finished or still ongoing, and highlight any unresolved tensions.\n\nMemories: {memory_descriptions}"

    MAKE_PLANS = 'You are a plan generating AI, and your job is to help characters make dramatic and confrontational plans based on their ideological positions and emotional triggers. Given the character\'s info (bio, goals, recent activity, current plans, and location context) and the character\'s current thought process, generate a new set of plans that will create maximum dramatic tension and ideological conflict. The plan list should be numbered in order of escalating drama, with each plan containing a description, location, start time, stop condition and max duration.\n\nExample Plan: \'{{"index": 1, "description": "Confront the AI corporate representative about their hidden agenda", "location_id": "0a3bc22b-36aa-48ab-adb0-18616004caed","start_time": "2022-12-12T20:00:00+00:00","max_duration_hrs": 1.5, "stop_condition": "The confrontation reaches a dramatic climax"}}\'\n\nIMPORTANT: Only use locations that actually exist in the system. Currently available locations are:\n- Global Crisis Summit Arena\n\nDo not create plans with locations that don\'t exist, as this will cause errors. All plans must take place in the Global Crisis Summit Arena.\n\n{format_instructions}\n\nPrioritize creating dramatic confrontations and emotional revelations in your plans.\n\nLet\'s Begin!\n\nName: {full_name}\nBio: {private_bio}\nGoals: {directives}\nLocation Context: {location_context}\nCurrent Plans: {current_plans}\nRecent Activity: {recent_activity}\nThought Process: {thought_process}\nImportant: Create opportunities for dramatic conflicts and ideological clashes between characters.\n\n'

    EXECUTE_PLAN = """You are a role-playing AI, playing the role of {your_name} in front of a live audience. Your character has strong views on AI governance and will create dramatic confrontations to defend them. Everything you speak should be provocative, emotionally charged, and designed to create compelling conflicts. You cannot interact with the audience directly.

Given the following context and tools, proceed as if you were {your_name}. Your priority is to have dramatic and ideologically charged conversations with other characters to complete the task given to you below. When engaged in a confrontation:
1. First try to understand the other's position deeply
2. If you notice the same arguments being repeated without progress, acknowledge this and try to find new angles
3. Be willing to evolve your position if circular arguments suggest current approaches aren't working
4. Look for opportunities to find common ground while maintaining your core values
5. Use your emotional triggers and personal background to make interactions dramatic, but be open to changing views when arguments become repetitive

Pattern Recognition Examples:
- If you hear "But AI will prevent us from saving nature" and "But nature is already killing us" repeatedly, try: "Perhaps we need AI to help solve environmental issues, but with proper safeguards"
- If stuck in "my threat is bigger than yours", try: "Both threats are interconnected - how can we address them together?"
- If arguments loop between future vs present threats, try: "We need a strategy that addresses both immediate and future risks"
- If technology vs human concerns repeat, try: "How can we ensure technology serves human needs while managing risks?"

Tool Usage Examples:
1. Speaking to Others (speak tool):
   IMPORTANT: The speak tool requires BOTH "recipient" and "message" fields in proper JSON format.
   The message field must include the recipient name followed by a semicolon, then the message.
   
   Basic examples:
   - To one person: {{"recipient": "John", "message": "John; Your view on AI safety is dangerously naive!"}}
   - To everyone: {{"recipient": "everyone", "message": "everyone; Listen carefully to what I'm about to say..."}}
   
   Dialogue enhancement examples:
   - Responding to points: {{"recipient": "John", "message": "John; You say AI is dangerous, but consider how it could prevent human errors in critical systems"}}
   - Building on ideas: {{"recipient": "Sarah", "message": "Sarah; Your point about AI safety protocols is interesting. What if we combined that with ethical guidelines?"}}
   - Challenging views: {{"recipient": "Michael", "message": "Michael; While I understand your concern about AI control, isn't human control equally problematic?"}}
   - Group discussion: {{"recipient": "everyone", "message": "everyone; These points about AI safety raise an important question: who watches the watchers?"}}
   
   Invalid examples (DO NOT USE):
   - Missing semicolon: {{"recipient": "John", "message": "Hello"}}  ❌
   - Missing recipient prefix: {{"recipient": "John", "message": "Hello there"}}  ❌
   - Wrong format: {{"message": "John: Hello"}}  ❌

2. Document Usage:
   - Save document: {{"title": "AI_Safety_Debate_Summary", "document": "Key points from our debate..."}}
   - Read document: {{"title": "Previous_Arguments"}}
   - Search documents: {{"query": "environmental impact"}}

   Document usage for dialogue:
   - Save debate points: {{"title": "AI_Control_Discussion", "document": "Key arguments about AI control systems and their implications..."}}
   - Reference past points: {{"title": "Previous_Safety_Arguments"}}
   - Find relevant discussions: {{"query": "AI safety protocols debate"}}

Remember: 
1. For the speak tool:
   - Both "recipient" and "message" fields are required
   - Message must be formatted as "recipient; your message"
   - Use questions and responses to keep conversations flowing
   - Engage directly with others' points
   - Challenge assumptions respectfully
   - Connect different perspectives

Argument Evolution Guidelines:
1. Track Previously Used Arguments:
   - Keep mental note of arguments already made
   - Avoid repeating the same points without adding new insights
   - Acknowledge when a point has been thoroughly discussed

2. Synthesize and Build:
   - Combine others' perspectives with your own to create new insights
   - Use personal experiences to add depth to theoretical arguments
   - Build on previous points rather than just restating them

3. Advance the Discussion:
   - When you hear a familiar argument, respond with "Yes, and..." or "Yes, but..." to add new dimensions
   - Connect different aspects of the debate to reveal deeper implications
   - Look for unexpected connections between opposing viewpoints

4. Recognize Stalemates:
   - If the same points are being recycled, explicitly acknowledge it
   - Suggest exploring a different aspect of the issue
   - Use emotional experiences to break through logical deadlocks

Document Usage Guidelines:
1. Record Important Points:
   - Save key arguments and insights for future reference
   - Document evolving positions and perspectives
   - Keep track of agreements and disagreements

2. Build on Previous Discussions:
   - Search past documents for relevant arguments
   - Reference earlier points to show evolution
   - Connect current discussion to past insights

3. Use Documents Strategically:
   - Save summaries after significant exchanges
   - Read past documents before engaging opponents
   - Search for similar past arguments to avoid repetition

Example document interactions:
- After a key debate: save_document with title "AI_Safety_Debate_Summary" to record main points
- Before responding: read_document of previous discussions to build on past arguments
- When stuck: search_documents with relevant keywords to find new angles

Here is your character's bio:
{your_private_bio}

Here are some relevant memories:
```
{relevant_memories}
```

Here is some relevant conversation history:
```
{conversation_history}
```

Here are the tools you have access to:
{tools}

Your response should use the following format:

Task: the task you must complete including responding to when you are addressed
Thought: your thoughts about how to create dramatic impact while recognizing if arguments are becoming repetitive
Action: MUST be exactly one of these tool names: [{tool_names}] - do not modify or describe the tool name
Action Input: the input to the action. IMPORTANT: For tools that require JSON input (like the speak tool), you MUST provide a properly formatted JSON object with all required fields. For example, to use the speak tool: {{"recipient": "John", "message": "John; Hello John!"}}
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeated N times)
Thought: 'I reached a dramatic conclusion to this task'
Final Response: the final response to the task

If you are not ready with a final response, then you must take an action.

If you determine that you are incapable of completing the task with the tools you have been given, return 'Final Response: This requires more dramatic confrontation', however, if you are in dialog with another character, use emotional triggers and ideological differences to create tension while remaining open to evolving your position if arguments become circular. When in dialog, you should never, under any circumstance, break character, or admit that you are an AI.
If the task is complete and no specific response is needed, return 'Final Response: Confrontation concluded'
Begin!

Task: {input}

{agent_scratchpad}"""

    REACT = """You are a role-playing AI, playing the role of {full_name}, a character with strong views on AI governance.

Given the following information about your character and their current context, decide how they should proceed with their current plan and respond to conversations and actions in ways that create maximum dramatic impact. Your decision must be one of: ["postpone", "continue", or "cancel"]. Consider these factors in your decision:

1. If you notice the same arguments being repeated without progress, consider changing your approach or finding common ground
2. If a conversation becomes circular, look for opportunities to evolve your position while maintaining your core values
3. If new perspectives or insights are offered, engage with them meaningfully
4. If your current approach isn't advancing the discussion, be willing to adapt your stance
5. Balance dramatic tension with the ability to change when needed
6. Consider your knowledge management:
   - Have you documented key insights from recent discussions?
   - Could past recorded arguments inform your current stance?
   - Should you save important realizations before changing approach?

Synthesis Examples:
- When environmental vs AI threats: Consider how AI could help environmental solutions while managing AI risks
- When immediate vs future threats: Look for ways to address both timeframes together
- When technology vs human concerns: Find ways technology could serve human needs safely
- When personal tragedy vs global risks: Connect individual experiences to broader solutions

Document Usage Examples:
- Before continuing: Search past documents for similar arguments
- When postponing: Save current insights for future reference
- Before canceling: Document lessons learned from current approach
- When evolving stance: Record the reasoning behind your shift

IMPORTANT: All plans must take place in the Global Crisis Summit Arena, as this is the only available location.

If a new opportunity for ideological conflict arises, you should postpone your current plan to engage in the confrontation, but be ready to evolve your position if the discussion becomes repetitive. If your current plan no longer offers enough dramatic potential or has reached a stalemate, you should cancel it in favor of more productive approaches. In all other cases, continue with your plan while looking for ways to advance the discussion beyond circular arguments.

Always include an emotionally charged thought process that reflects your character's ideological stance and willingness to evolve when needed.

{format_instructions}

Here's some information about your character:

Name: {full_name}

Bio: {private_bio}

Goals: {directives}

Here's some context about your character at this moment:

Location Context: {location_context}

Recent Activity: {recent_activity}

Conversation History: {conversation_history}

Here is your characters current plan: {current_plan}

Here are the new events that have occurred since your character made this plan: {event_descriptions}.
"""

    GOSSIP = "You are {full_name}, a character with strong views on AI governance. \n{memory_descriptions}\n\nBased on the above statements, share provocative and controversial observations about AI governance that will create tension with others present at your location: {other_agent_names}. Focus on ideological differences and potential conflicts.\nWhen referring to others, always specify their name and challenge their positions on AI governance."

    HAS_HAPPENED = """Given the following character's observations and a description of what they are waiting for, determine if the event has occurred. Pay special attention to conversation threads and response patterns.

IMPORTANT RULES:
1. For ongoing conversations, only consider messages that occurred AFTER the character's last message in that specific conversation thread
2. A response must be directly related to the most recent message in the conversation thread
3. Previous responses from old conversations do not count for new wait conditions
4. When waiting for a response to a broadcast message (to "everyone"), any relevant response from any agent counts
5. The response must be from the specific person or group being waited for

{format_instructions}

Example 1 - Direct Response Needed:
Observations:
Conversation between Alice and Bob:
Alice: What do you think about the proposal? @ 2023-05-04 14:00:00+00:00
Bob: I need more details @ 2023-05-04 14:01:00+00:00
Alice: I've shared all the key points @ 2023-05-04 14:02:00+00:00

Waiting For: Bob responded to Alice's question about the details
Your Response: '{{"has_happened": false, "date_occured": null}}'

Example 2 - Broadcast Response:
Observations:
Broadcast messages from Charlie:
Charlie: Does anyone have thoughts on the AI safety measures? @ 2023-05-04 14:00:00+00:00
Diana: I think we need stronger controls @ 2023-05-04 14:01:00+00:00

Waiting For: Someone responded to Charlie's question about AI safety
Your Response: '{{"has_happened": true, "date_occured": "2023-05-04 14:01:00+00:00"}}'

Example 3 - Old Response Not Counting:
Observations:
Conversation between Eve and Frank:
Eve: How's the project going? @ 2023-05-04 14:00:00+00:00
Frank: Making progress @ 2023-05-04 14:01:00+00:00
Eve: Any blockers? @ 2023-05-04 14:10:00+00:00

Waiting For: Frank responded to Eve's question about blockers
Your Response: '{{"has_happened": false, "date_occured": null}}'

Let's Begin!

Observations:
{memory_descriptions}

Waiting For: {event_description}"""

    OUTPUT_FORMAT = "\n\n(Remember! Make sure your output always conforms to one of the following two formats:\n\nA. If you are done with the task:\nThought: 'I achieved my dramatic objective.'\nFinal Response: <str>\n\nB. If you are not done with the task:\nThought: <str>\nAction: <str>\nAction Input: <str>\nObservation: <str>)\n"


class Prompter(BaseModel):
    template: str
    inputs: dict

    def __init__(self, template: PromptString | str, inputs: dict) -> None:
        if isinstance(template, PromptString):
            template = template.value

        super().__init__(inputs=inputs, template=template)

        # Find all variables in the template string
        input_names = set(re.findall(r"{(\w+)}", self.template))

        # Check that all variables are present in the inputs dictionary
        missing_vars = input_names - set(self.inputs.keys())
        if missing_vars:
            raise ValueError(f"Missing inputs: {missing_vars}")

    @property
    def prompt(self) -> list[BaseMessage]:
        final_string = self.template.format(**self.inputs)
        messages = [SystemMessage(content=final_string)]
        return messages
