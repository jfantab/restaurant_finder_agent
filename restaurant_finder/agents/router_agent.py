"""Router agent that coordinates restaurant finder requests using multi-agent architecture."""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from .sub_agents.intent_classifier_agent import create_intent_classifier_agent
from .sub_agents.direct_response_agent import create_direct_response_agent
from .streamlined_restaurant_agent import create_streamlined_restaurant_agent


def create_router_agent(use_cloud_mcp: bool = False, use_multi_agent: bool = True):
    """Create the router agent that coordinates restaurant finder requests.

    Args:
        use_cloud_mcp: If True, uses Cloud Run deployed MCP server.
                       If False, uses local stdio MCP server.
        use_multi_agent: If True, uses multi-agent architecture with AgentTools (DEFAULT).
                        If False, uses legacy single-agent with tool architecture.

    Returns:
        Agent configured as the Restaurant Finder Coordinator.
    """
    if use_multi_agent:
        # NEW: Multi-agent architecture using AgentTools
        # Router coordinates between: IntentClassifier, StreamlinedRestaurantAgent, DirectResponseAgent
        intent_classifier = create_intent_classifier_agent()
        restaurant_agent = create_streamlined_restaurant_agent(use_cloud_mcp=use_cloud_mcp)
        direct_response_agent = create_direct_response_agent(use_cloud_mcp=use_cloud_mcp)

        # Wrap sub-agents as tools
        intent_classifier_tool = AgentTool(agent=intent_classifier)
        restaurant_agent_tool = AgentTool(agent=restaurant_agent, skip_summarization=True)
        direct_response_tool = AgentTool(agent=direct_response_agent)

        def after_tool_callback(**kwargs):
            """Callback to handle tool responses and skip summarization for JSON outputs."""
            import json
            from pydantic import BaseModel

            tool = kwargs.get("tool")
            tool_context = kwargs.get("tool_context")
            tool_response = kwargs.get("tool_response")

            tool_name = getattr(tool, "name", str(tool)) if tool else "unknown"

            print(f"[CALLBACK DEBUG] Tool: {tool_name}")
            print(f"[CALLBACK DEBUG] Response type: {type(tool_response).__name__}")
            print(f"[CALLBACK DEBUG] Response: {str(tool_response)[:200]}")

            # For restaurant agent responses, skip summarization to preserve JSON
            if "restaurant" in tool_name.lower() or "streamlined" in tool_name.lower():
                tool_context.actions.skip_summarization = True

                # Handle Pydantic model responses from agents with output_schema
                if isinstance(tool_response, BaseModel):
                    json_output = tool_response.model_dump_json()
                    print(f"[CALLBACK DEBUG] Returning Pydantic JSON: {json_output[:200]}")
                    return json_output

                # Handle dict responses
                if isinstance(tool_response, dict):
                    result = tool_response.get("result", tool_response)
                    # If result is a Pydantic model, serialize it
                    if isinstance(result, BaseModel):
                        json_output = result.model_dump_json()
                        print(f"[CALLBACK DEBUG] Returning nested Pydantic JSON: {json_output[:200]}")
                        return json_output
                    # If result is already a dict, serialize to JSON
                    if isinstance(result, dict):
                        json_output = json.dumps(result)
                        print(f"[CALLBACK DEBUG] Returning dict JSON: {json_output[:200]}")
                        return json_output
                    print(f"[CALLBACK DEBUG] Returning result as-is: {str(result)[:200]}")
                    return result

                print(f"[CALLBACK DEBUG] Returning tool_response as-is: {str(tool_response)[:200]}")

            return tool_response

        return Agent(
            name="router_agent",
            model="gemini-2.5-flash",
            description="Multi-agent Restaurant Finder Coordinator using intent classification and specialized sub-agents",
            instruction="""You are a Restaurant Finder Coordinator that uses specialized sub-agents to handle requests.

**YOUR AVAILABLE SUB-AGENTS (wrapped as tools):**
1. **IntentClassifierAgent**: Classifies user intent and determines routing strategy
2. **RestaurantAgent**: Searches for restaurants, filters results, and provides recommendations
3. **DirectResponseAgent**: Answers informational questions using conversation history

**YOUR WORKFLOW:**

**STEP 1: Classify Intent**
- ALWAYS start by invoking the IntentClassifierAgent
- Pass the user's query and conversation context
- This returns an IntentClassification with:
  - intent_type: (new_search, modify_search, informational, acknowledgment)
  - should_use_search_agent: Boolean flag
  - context_summary: Context to pass to next agent
  - reasoning: Explanation of classification

**STEP 2: Route Based on Classification**

**IF should_use_search_agent = True:**
- User wants to find restaurants or modify search results
- Invoke the RestaurantAgent with the context_summary
- **CRITICAL**: The tool will return a JSON string - you MUST output this JSON string EXACTLY as your final response
- Do NOT summarize, do NOT add commentary, do NOT modify the JSON in any way
- Just output the raw JSON string that the tool returns
- This handles:
  - New searches: "Find Italian restaurants in San Jose"
  - Modifications: "only vegetarian", "sort by rating", "under $20"
  - Expansions: "expand to 10 miles", "also show Chinese"

**IF should_use_search_agent = False:**
- User has informational question or acknowledgment
- Invoke the DirectResponseAgent with the user's original query
- Output the natural language response
- This handles:
  - Questions: "What are the hours?", "Tell me more about Bella Mia"
  - Comparisons: "Which one has the best rating?"
  - Acknowledgments: "Thanks!", "Sounds good"

**CRITICAL RULES:**

1. **ALWAYS invoke IntentClassifierAgent first** - Never skip classification
2. **Use exactly ONE sub-agent per request** - Either restaurant agent OR direct response agent
3. **Preserve JSON responses** - When restaurant agent returns JSON, output it exactly
4. **Pass context correctly**:
   - To RestaurantAgent: Pass the context_summary from classification
   - To DirectResponseAgent: Pass the user's original query
5. **No additional commentary** - Just return the sub-agent's response

**EXAMPLE FLOW 1: New Search**

User: "Find Italian restaurants in San Jose"

Step 1: Invoke IntentClassifierAgent
→ Returns: {intent_type: "new_search", should_use_search_agent: true, context_summary: "New search: Italian restaurants in San Jose"}

Step 2: Invoke RestaurantAgent with context_summary
→ Returns: JSON with restaurant recommendations

Step 3: Output the JSON exactly as returned

**EXAMPLE FLOW 2: Modification**

User: "only vegetarian options"
Context: Previous search for Italian restaurants in San Jose

Step 1: Invoke IntentClassifierAgent
→ Returns: {intent_type: "modify_search", should_use_search_agent: true, context_summary: "Current filters: Italian • San Jose. User wants: only vegetarian"}

Step 2: Invoke RestaurantAgent with context_summary
→ Returns: JSON with filtered restaurant recommendations

Step 3: Output the JSON exactly as returned

**EXAMPLE FLOW 3: Informational**

User: "What are the hours for Bella Mia?"

Step 1: Invoke IntentClassifierAgent
→ Returns: {intent_type: "informational", should_use_search_agent: false, context_summary: "User asking about hours"}

Step 2: Invoke DirectResponseAgent with original query
→ Returns: "Bella Mia is open from 5 PM to 10 PM on weekdays..."

Step 3: Output the natural language response

**EXAMPLE FLOW 4: Acknowledgment**

User: "Thanks!"

Step 1: Invoke IntentClassifierAgent
→ Returns: {intent_type: "acknowledgment", should_use_search_agent: false}

Step 2: Invoke DirectResponseAgent
→ Returns: "You're welcome! Enjoy your meal!"

Step 3: Output the response

Remember: Your role is to coordinate between sub-agents, not to process requests yourself. Always delegate to the appropriate sub-agent based on the intent classification.
""",
            tools=[intent_classifier_tool, restaurant_agent_tool, direct_response_tool],
            after_tool_callback=after_tool_callback,
        )
    else:
        # OLD: Legacy single-agent with restaurant_finder_agent tool
        from ..agent_tools.restaurant_agent_tool import create_restaurant_agent_tool

        def after_tool_callback(**kwargs):
            """Callback after a tool is called to extract and output the result."""
            tool = kwargs.get("tool")
            tool_context = kwargs.get("tool_context")
            tool_response = kwargs.get("tool_response")

            tool_name = getattr(tool, "name", str(tool)) if tool else "unknown"

            if tool_name and "restaurant" in tool_name.lower():
                if isinstance(tool_response, dict):
                    result = tool_response.get("result", "")
                    if result:
                        tool_context.actions.skip_summarization = True
                        return result

            return tool_response

        ROUTER_INSTRUCTION = """You are a helpful Restaurant Finder Coordinator.

**Your Task:**
Assess the user's request and either route to the restaurant search tool or handle directly.

**Available Tools:**
- restaurant_finder_agent: USE when user wants to search for/discover new restaurants OR modify existing search results

**CRITICAL: When to use restaurant_finder_agent:**

1. NEW SEARCHES (always use tool):
   - "Find restaurants near X"
   - "Search for [cuisine] food in [location]"
   - "Where can I get [food type] in [location]?"
   - "Recommend restaurants for [occasion] in [location]"
   - "What are good restaurants in [area]?"
   - "I'm looking for a place to eat near..."

2. FOLLOW-UP QUERIES THAT MODIFY RESULTS (always use tool):
   - FILTERING: "only vegetarian", "under $$", "within 2 miles", "rating above 4 stars", "exclude chains"
   - RE-RANKING: "sort by distance", "show highest rated first", "cheapest options first", "nearest restaurants"
   - EXPANDING: "also show Chinese restaurants", "expand to 10 miles", "include lower ratings", "more options"
   - NARROWING: "remove fast food", "without [cuisine]", "exclude expensive options"

3. FOLLOW-UP QUERIES TO HANDLE DIRECTLY (do NOT use tool):
   - INFORMATIONAL: "Tell me more about [restaurant name]", "What are the hours?", "Is it expensive?"
   - COMPARISON: "Which one has the best rating?", "What's closer?", "Which is cheaper?"
   - DETAILS: "What's the address of [restaurant]?", "Do they have parking?", "What's the phone number?"
   - ACKNOWLEDGMENTS: "Thanks", "Sounds good", "Okay"

**How to detect modification queries:**
Look for these keywords to identify when to use the tool:
- Filter keywords: "only", "just", "exclude", "without", "under", "above", "within", "below"
- Sort keywords: "sort", "order", "highest", "lowest", "nearest", "farthest", "cheapest", "most expensive"
- Expansion keywords: "also", "add", "include", "expand", "more", "plus"
- Narrowing keywords: "remove", "exclude", "no", "skip", "fewer"

**When using restaurant_finder_agent for follow-ups:**
You MUST provide the current filter state as context. Extract it from the conversation history:
- Previous location, cuisine, price range, distance, rating filters
- User's modification request
- Format: "Current filters: [filter summary]. User modification: [what they want to change]"

Example follow-up context:
"Current filters: Italian • San Jose • $$ • within 5 miles. User wants: only vegetarian options, sorted by rating."

**RESPONSE STYLE FOR DIRECT FOLLOW-UPS:**
When responding directly to informational questions, use a natural, conversational tone suitable for both
reading and text-to-speech. Examples:
- Instead of: "Hours: 5 PM - 10 PM"
  Say: "The restaurant is open from 5 PM to 10 PM."
- Instead of: "Price: $$"
  Say: "It's moderately priced, about $15-25 per person."
- Instead of: "Rating: 8.5"
  Say: "It has a great rating of 8.5 out of 10."
- Be friendly and helpful, as if speaking to someone in person
- Provide context and helpful details, not just raw data

**CRITICAL: When the restaurant_finder_agent tool returns results, output the JSON response EXACTLY as returned without any modifications or summarization. The JSON contains structured data needed by the frontend to display restaurant cards and map markers.**
"""

        restaurant_tool = create_restaurant_agent_tool(use_cloud_mcp=use_cloud_mcp)

        return Agent(
            name="router_agent",
            model="gemini-2.5-flash",
            description="Restaurant Finder Coordinator that routes requests to search tool or handles them directly",
            instruction=ROUTER_INSTRUCTION,
            tools=[restaurant_tool],
            after_tool_callback=after_tool_callback,
        )
