const blessed = require('blessed');
const WebSocket = require('ws');

// Shared In-Memory State
const state = {
  agents: new Map()
};

// WebSocket Server (IPC)
const wss = new WebSocket.Server({ port: 8084 });

wss.on('connection', function connection(ws) {
  ws.on('message', function incoming(message) {
    try {
      const data = JSON.parse(message);
      if (data.type === 'AgentStart') {
        state.agents.set(data.id, {
          name: data.name,
          status: 'Started',
          tokens: 0,
          context_limit: 128000
        });
      } else if (data.type === 'StatusUpdate') {
        const agent = state.agents.get(data.id);
        if (agent) agent.status = data.status;
      } else if (data.type === 'TokenUpdate') {
        const agent = state.agents.get(data.id);
        if (agent) {
          agent.tokens = data.tokens_used;
          agent.context_limit = data.context_limit;
        }
      }
      render();
    } catch (e) {
      // Ignore invalid JSON payloads to prevent crashing
    }
  });
});

// Terminal UI Initialization
const screen = blessed.screen({
  smartCSR: true,
  title: 'VIGIL - AI Agent Monitor'
});

const header = blessed.box({
  parent: screen,
  top: 0,
  left: 0,
  width: '100%',
  height: 3,
  content: '{bold}{cyan-fg}VIGIL - AI Agent Monitor{/cyan-fg}{/bold} | ws://127.0.0.1:8084 | Press Q to quit | Press K to kill all',
  tags: true,
  border: { type: 'line' },
  style: { border: { fg: '#f0f0f0' } }
});

const agentsContainer = blessed.box({
  parent: screen,
  top: 3,
  left: 0,
  width: '100%',
  height: '100%-3',
  scrollable: true,
  alwaysScroll: true
});

screen.key(['escape', 'q', 'C-c'], function(ch, key) {
  return process.exit(0);
});

// Circuit Breaker: Send Kill command to all connected clients
screen.key(['k', 'K'], function(ch, key) {
  wss.clients.forEach(function each(client) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({ type: 'Kill' }));
    }
  });
});

let agentBoxes = new Map();

// Immediate-mode Rendering Logic
function render() {
  if (process.env.VIGIL_TEST_MODE === '1') return;

  state.agents.forEach((agent, id) => {
    if (!agentBoxes.has(id)) {
      const box = blessed.box({
        parent: agentsContainer,
        width: '100%',
        height: 6,
        border: { type: 'line' },
        tags: true,
        top: agentBoxes.size * 6
      });
      agentBoxes.set(id, box);
    }
    
    const box = agentBoxes.get(id);
    const ratio = agent.context_limit > 0 ? Math.min(agent.tokens / agent.context_limit, 1) : 0;
    const barLength = 40;
    const filled = Math.floor(ratio * barLength);
    const bar = '{green-bg}' + ' '.repeat(filled) + '{/green-bg}' + '{white-bg}' + ' '.repeat(barLength - filled) + '{/white-bg}';
    
    const statusColor = agent.status.toLowerCase().includes('error') ? '{red-fg}' : '{green-fg}';

    box.setContent(
      `{bold}Agent:{/bold} ${agent.name} (ID: ${id})\n` +
      `{bold}Status:{/bold} ${statusColor}${agent.status}{/}\n` +
      `{bold}Context:{/bold} ${agent.tokens} / ${agent.context_limit} tokens\n` +
      `[${bar}] ${(ratio*100).toFixed(1)}%`
    );
  });
  
  screen.render();
}

if (process.env.VIGIL_TEST_MODE === '1') {
  console.log("Test mode enabled. Bypassing UI loop and exiting cleanly.");
  process.exit(0);
}

render();
