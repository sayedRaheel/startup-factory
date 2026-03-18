import asyncio
import websockets
import json
import threading
import time

class VigilCircuitBreakerException(Exception):
    """Raised when the developer hits 'K' in the terminal."""
    pass

class Vigil:
    def __init__(self, port=8084):
        self.uri = f"ws://127.0.0.1:{port}"
        self.loop = asyncio.new_event_loop()
        self.ws = None
        self._killed = False
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._thread.start()
        # Give background thread a moment to bind socket
        time.sleep(0.1)

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect())
        self.loop.run_forever()

    async def _connect(self):
        try:
            self.ws = await websockets.connect(self.uri)
            asyncio.create_task(self._listen_for_kills())
        except Exception:
            # Silent failure if the CLI monitor isn't running. Agent should not crash.
            pass

    async def _listen_for_kills(self):
        while True:
            if self.ws:
                try:
                    msg = await self.ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "Kill":
                        self._killed = True
                except Exception:
                    break
            else:
                await asyncio.sleep(1)

    def check_kill_switch(self):
        if self._killed:
            raise VigilCircuitBreakerException("VIGIL INTERCEPT: Execution killed by user from CLI.")

    def emit(self, telemetry_dict):
        self.check_kill_switch()
        async def _send():
            if self.ws and self.ws.open:
                try:
                    await self.ws.send(json.dumps(telemetry_dict))
                except Exception:
                    pass
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), self.loop)

    def hook(self, agent_name, agent_id="main"):
        self.emit({"type": "AgentStart", "id": agent_id, "name": agent_name})
        
        class AgentWrapper:
            def __init__(self, vigil_instance, a_id):
                self._v = vigil_instance
                self.agent_id = a_id

            def update_status(self, status):
                self._v.emit({"type": "StatusUpdate", "id": self.agent_id, "status": status})
                
            def update_tokens(self, used, limit=128000):
                self._v.emit({"type": "TokenUpdate", "id": self.agent_id, "tokens_used": used, "context_limit": limit})
                
            def check(self):
                self._v.check_kill_switch()
        
        return AgentWrapper(self, agent_id)
