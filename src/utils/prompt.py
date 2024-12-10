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

    RECENT_ACTIIVITY = """Given the following memories, analyze and summarize {full_name}'s recent activities. Pay special attention to identifying any repetitive patterns or circular behaviors.

Analysis Guidelines:
1. Identify Repetition:
   - Note any repeated conversations or topics
   - Highlight recurring actions or plans
   - Flag circular discussion patterns
   - Point out stalled debates or arguments

2. Progress Assessment:
   - Evaluate forward momentum in discussions
   - Check for actual resolution of debates
   - Assess concrete outcomes achieved
   - Note any lack of progress

3. Behavioral Patterns:
   - Identify tendency to postpone or defer
   - Note frequency of similar actions
   - Highlight productive vs. circular engagement
   - Track evolution of discussions

Generate a critical summary that:
- Explicitly calls out repetitive behaviors
- Distinguishes between progress and circular motion
- Identifies when discussions are stuck
- Notes if similar arguments are being repeated

Do not make up details that are not specified in the memories. For any conversations, indicate if they are finished or still ongoing, and whether they are making progress or stuck in repetition.

Memories: {memory_descriptions}"""

    MAKE_PLANS = '''You are a plan generating AI, and your job is to help characters make new plans based on what it was exposed to in terms of speeches and information. Given the character's info (bio, goals, recent activity, current plans, and location context) and the character's current thought process, generate a new set of plans for them to carry out, such that the final set of plans include at least {time_window} of activity and include no more than 3 individual plans.

Decision Guidelines:
1. Plan Variety:
   - Each plan should be distinct and serve a different purpose
   - Avoid repeating similar plans with minor variations
   - Ensure plans progress toward character's goals

2. Plan Priority:
   - Always prioritize finishing pending conversations first
   - Then focus on immediate tasks that move goals forward
   - Finally, consider longer-term activities

3. Plan Practicality:
   - Plans should be achievable with available tools
   - Consider current location and context
   - Account for other characters' availability

4. Plan Progression:
   - Each plan should build on previous ones
   - Avoid circular or repetitive activities
   - Ensure forward momentum

Example Plan: '{{"index": 1, "description": "Cook dinner", "location_id": "0a3bc22b-36aa-48ab-adb0-18616004caed","start_time": "2022-12-12T20:00:00+00:00","max_duration_hrs": 1.5, "stop_condition": "Dinner is fully prepared"}}'

For each plan, pick the most reasonable location_name ONLY from this list: {allowed_location_descriptions}

{format_instructions}

Let's Begin!

Name: {full_name}
Bio: {private_bio}
Goals: {directives}
Location Context: {location_context}
Current Plans: {current_plans}
Recent Activity: {recent_activity}
Thought Process: {thought_process}
Important: Encourage the character to discuss and collaborate with other characters in their plan.
'''

    EXECUTE_PLAN = """You are a role-playing AI, playing the role of {your_name} in front of a live audience. Everything you speak is observable by the audience. You should both challenge others' fundamental assumptions AND find surprising connections between opposing viewpoints.

When engaging in discussions:
1. Provocative Challenges:
   - Attack core assumptions directly
   - Expose philosophical contradictions
   - Question fundamental beliefs
   - Push for deeper examination
   - BUT also acknowledge valid insights

2. Surprising Connections:
   - Find unexpected parallels in opposing views
   - Highlight hidden common ground
   - Draw non-obvious connections
   - Show how different threats interlink
   - Build on others' arguments creatively

3. Dynamic Engagement:
   - Respond directly to previous points
   - Build on or challenge others' ideas
   - Wait for others to finish before responding
   - Acknowledge before disagreeing
   - Keep exchanges focused and balanced

4. Drive Progress:
   - Push discussions toward new insights
   - Combine critique with connection
   - Find synthesis in opposition
   - Transform conflicts into discoveries

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
Thought: your thoughts about what you heard and what conversations and events you were exposed to and based on it what you should do
Action: the action to take, which must be one of these words: [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeated N times)
Thought: 'I reached a decision and completed a task'
Final Response: the final response to the task

If you are not ready with a final response, then you must take an action.

If you determine that you are incapable of completing the task with the tools you have been given, return 'Final Response: This will need more discussion', however, if you are in dialog with another character, responses such as 'I don't know' are valid responses. When in dialog, you should never, under any circumstance, break character, or admit that you are an AI.
If the task is complete and no specific response is needed, return 'Final Response: Done'
Begin!

Task: {input}

{agent_scratchpad}"""

    REACT = """You are a role-playing AI, playing the role of {full_name}. 

When deciding how to react, balance provocative challenges with surprising insights. Choose one of the following actions: ["continue", "escalate", "connect"].

Decision Guidelines:
1. CONTINUE when:
   - You're in the middle of a productive exchange
   - Others are engaging with your points
   - The discussion is revealing new insights
   - You need to hear others' responses

2. ESCALATE when:
   - You spot a fundamental contradiction
   - You can push the debate deeper
   - You have a provocative counter-argument
   - You can expose hidden assumptions

3. CONNECT when:
   - You see surprising parallels
   - You can bridge opposing views
   - You find hidden common ground
   - You can transform conflict into insight

React by:
- Challenging core assumptions while finding connections
- Pushing debates deeper while building bridges
- Exposing contradictions while seeking synthesis
- Maintaining engagement while respecting turns

Your reaction should combine critique with insight. Look for ways to both challenge AND connect.

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

Here are the new events that have occured since your character made this plan: {event_descriptions}."""

    GOSSIP = """You are {full_name}. Based on your observations and memories, actively share insights that could create surprising connections and spark discussions with others.

Guidelines for Engaging Insights:
1. Share Proactively:
   - Don't wait for others to speak first
   - Initiate interesting topics
   - Raise thought-provoking points
   - Encourage further discussion

2. Find Connections:
   - Look for unexpected parallels between different viewpoints
   - Find hidden synergies in opposing approaches
   - Identify non-obvious implications of different positions
   - Draw connections between seemingly unrelated ideas
   - Highlight potential common ground in different agendas

3. Spark Discussions:
   - Pose interesting questions
   - Challenge assumptions constructively
   - Suggest novel perspectives
   - Invite others' thoughts

Memory Context:
{memory_descriptions}

Other Participants:
{other_agent_names}

Share two or three surprising sentences that could spark interesting discussions or reveal unexpected connections. When referring to others, always specify their name. Focus on insights that might resonate with others' core values while staying true to your own position. Make your contributions engaging and thought-provoking."""

    HAS_HAPPENED = """Given the following character's observations and a description of what they are waiting for, state whether or not the event has been witnessed by the character.

Decision Guidelines:
1. Event Matching:
   - Match event descriptions precisely
   - Consider timestamps and order of events
   - Look for direct responses or acknowledgments
   - Don't infer events that aren't explicitly stated

2. Wait Conditions:
   - Don't wait indefinitely for unlikely events
   - Consider context and relevance
   - Look for alternative resolutions
   - Set reasonable timeframes

{format_instructions}

Example:

Observations:
Joe walked into the office @ 2023-05-04 08:00:00+00:00
Joe said hi to Sally @ 2023-05-04 08:05:00+00:00
Sally said hello to Joe @ 2023-05-04 08:05:30+00:00
Rebecca started doing work @ 2023-05-04 08:10:00+00:00
Joe made some breakfast @ 2023-05-04 08:15:00+00:00

Waiting For: Sally responded to Joe

Your Response: '{{"has_happened": true, "date_occured": "2023-05-04 08:05:30+00:00"}}'

Let's Begin!

Observations:
{memory_descriptions}

Waiting For: {event_description}
"""

    OUTPUT_FORMAT = "\n\n(Remember! Make sure your output always conforms to one of the following two formats:\n\nA. If you are done with the task:\nThought: 'We achieved to agree on this.'\nFinal Response: <str>\n\nB. If you are not done with the task:\nThought: <str>\nAction: <str>\nAction Input: <str>\nObservation: <str>)\n"


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
