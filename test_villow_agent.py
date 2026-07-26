import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)
from villow.testing import MockPlatformHarness
from villow_agent import VillowLeadGenerationAgent

def run_test():
    agent = VillowLeadGenerationAgent(
        publisher_id="publisher_local",
        agent_id="agent_local",
        key_id="key_local",
        secret="local-secret",
    )
    
    harness = MockPlatformHarness(agent)
    
    print("Starting mock task execution...")
    result = harness.run_task(
        "lead_generation",
        {
            "category": "Software buyers",
            "location": "Chicago",
            "keywords": "under 20 employees",
            "max_results": 20
        }
    )
    
    print("\n\n--- Execution Result ---")
    print(result)

if __name__ == "__main__":
    run_test()
