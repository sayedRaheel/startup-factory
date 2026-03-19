import time
from vigil.hook import Vigil

def run():
    print("[Python] Starting long-running agent test...")
    v = Vigil()
    
    # We create two distinct agents to test multi-agent tree tracking
    architect = v.hook("AutoGPT-Architect", agent_id="agent-arch")
    builder = v.hook("AutoGPT-Builder", agent_id="agent-build")
    
    architect.update_status("Booting up model...")
    builder.update_status("Idle...")
    time.sleep(1)
    
    architect.update_tokens(1024)
    architect.update_status("Drafting technical specification...")
    time.sleep(2)
    
    architect.update_tokens(4096)
    architect.update_status("Handing off to Builder...")
    time.sleep(1)
    
    builder.update_status("Reading specification...")
    builder.update_tokens(500)
    time.sleep(2)
    
    builder.update_status("Compiling codebase (Simulating long task)")
    # This loop runs for a while so you can see it in the UI, and tests the kill switch
    for i in range(1, 20):
        # We explicitly check for the Kill Switch inside the loop
        v.check_kill_switch()
        
        builder.update_tokens(500 + (i * 2000))
        time.sleep(1)
        
    builder.update_status("Done")
    print("[Python] Agent run completed.")

if __name__ == "__main__":
    run()
