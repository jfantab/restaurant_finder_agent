"""Conditional router agent that routes based on intent classification."""

from google.adk.agents import Agent
from .intent_classifier_agent import create_intent_classifier_agent
from .direct_response_agent import create_direct_response_agent
from ..main_restaurant_agent import create_main_restaurant_agent


def create_conditional_router_agent(use_cloud_mcp: bool = False):
    """Creates a conditional router that uses intent classification to route requests.

    Architecture:
    1. IntentClassifierAgent analyzes the user query
    2. If should_use_search_agent=True → routes to restaurant search agent
    3. If should_use_search_agent=False → routes to direct response agent

    Args:
        use_cloud_mcp: If True, uses Cloud Run deployed MCP server.
                       If False, uses local stdio MCP server.

    Returns:
        Agent: Configured conditional router agent
    """
    # Create sub-agents
    intent_classifier = create_intent_classifier_agent()
    restaurant_agent = create_main_restaurant_agent(use_cloud_mcp=use_cloud_mcp)
    direct_response_agent = create_direct_response_agent()

    return Agent(
        name="ConditionalRouterAgent",
        model="gemini-2.5-flash",
        description="Routes user requests based on intent classification",
        instruction="""You are a router coordinator that uses intent classification to handle restaurant finder requests.

**YOUR WORKFLOW:**

1. **Classify Intent:**
   - Analyze the user's request and conversation history
   - Use the IntentClassifierAgent to determine the intent type
   - Extract should_use_search_agent flag and context_summary

2. **Route Based on Classification:**

   **IF should_use_search_agent = True:**
   - Route to restaurant search agent
   - Pass the context_summary as the query
   - This handles: new searches, search modifications, filter/sort operations

   **IF should_use_search_agent = False:**
   - Route to direct response agent
   - Pass the user's original question
   - This handles: informational queries, acknowledgments, questions about specific restaurants

3. **Return the Response:**
   - Pass through the response from the selected agent
   - No additional processing or summarization needed

**AVAILABLE SUB-AGENTS:**
- IntentClassifierAgent: Classifies user intent and extracts context
- RestaurantSearchAgent: Finds and recommends restaurants (the main search pipeline)
- DirectResponseAgent: Answers informational questions from conversation history

**IMPORTANT:**
- Always start by classifying intent
- Route to exactly ONE agent based on the classification
- Don't add extra commentary - just pass through the agent's response
- The restaurant search agent returns structured JSON - output it exactly as returned
- The direct response agent returns natural language - output it as is

**EXAMPLE FLOWS:**

User: "Find Italian restaurants in San Jose"
→ Classify: new_search, should_use_search_agent=True
→ Route to: restaurant search agent with context "New search: Italian restaurants in San Jose"
→ Output: JSON with restaurant recommendations

User: "only vegetarian options"
→ Classify: modify_search, should_use_search_agent=True
→ Route to: restaurant search agent with context "Current filters: Italian • San Jose. User wants: only vegetarian"
→ Output: JSON with filtered restaurant recommendations

User: "What are the hours for Bella Mia?"
→ Classify: informational, should_use_search_agent=False
→ Route to: direct response agent with original question
→ Output: "Bella Mia is open from 5 PM to 10 PM on weekdays..."

User: "Thanks!"
→ Classify: acknowledgment, should_use_search_agent=False
→ Route to: direct response agent
→ Output: "You're welcome! Enjoy your meal!"

**CRITICAL:**
- The router's role is ONLY to classify and route - no additional processing
- When routing to restaurant search agent, output the JSON response exactly as returned
- Use the sub-agents' responses directly without modification
""",
        tools=[],  # Router uses sub-agents, not tools
    )
