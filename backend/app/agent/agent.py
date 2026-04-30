import json
import os
import anthropic

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools.sea_floor   import DEFINITION as SEA_FLOOR_DEF,  get_sea_floor_depth
from app.agent.tools.jma_warning import DEFINITION as JMA_DEF,        get_jma_warning_level
from app.agent.tools.tsunami_nn  import DEFINITION as TSUNAMI_NN_DEF, get_tsunami_nearest_neighbours

TOOL_DEFINITIONS = [SEA_FLOOR_DEF, JMA_DEF, TSUNAMI_NN_DEF]

TOOL_FUNCTIONS = {
    "get_sea_floor_depth"           : get_sea_floor_depth,
    "get_jma_warning_level"         : get_jma_warning_level,
    "get_tsunami_nearest_neighbours": get_tsunami_nearest_neighbours,
}

async def run_impact_agent(
    latitude: float,
    longitude: float,
    magnitude: float = 7.5
) -> dict:

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    messages = [{
        "role"   : "user",
        "content": (
            f"Assess the earthquake and tsunami impact potential "
            f"for latitude {latitude}, longitude {longitude} "
            f"with magnitude {magnitude}. "
            f"Complete all tool calls and return a full damage report as JSON."
        )
    }]

    while True:
        response = client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 2048,
            system     = SYSTEM_PROMPT,
            tools      = TOOL_DEFINITIONS,
            messages   = messages
        )

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    fn     = TOOL_FUNCTIONS[block.name]
                    result = await fn(**block.input)
                    tool_results.append({
                        "type"       : "tool_result",
                        "tool_use_id": block.id,
                        "content"    : json.dumps(result)
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user",      "content": tool_results})

        elif response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), "{}"
            )
            try:
                clean = (
                    final_text.strip()
                    .removeprefix("```json")
                    .removeprefix("```")
                    .removesuffix("```")
                    .strip()
                )
                return json.loads(clean)
            except json.JSONDecodeError:
                return {
                    "damage_summary": final_text,
                    "parse_error"   : True
                }
        else:
            break

    return {"error": "Agent did not complete successfully"}