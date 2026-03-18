import time
from vigil.hook import Vigil

def run():
    print("[Python] Starting agent test run...")
    v = Vigil()
    agent = v.hook("AutoGPT-Core", agent_id="agent-test-1")
    
    agent.update_status("Booting up model...")
    time.sleep(0.5)
    
    agent.update_tokens(1024)
    agent.update_status("Executing: search google for latest news")
    time.sleep(0.5)
    
    agent.update_tokens(5890)
    agent.update_status("Parsing 14 results...")
    time.sleep(0.5)
    
    agent.update_status("Done")
    print("[Python] Agent run completed.")

if __name__ == "__main__":
    run()
