require('dotenv').config();
const { start } = require('./server');

const port = parseInt(process.env.PORT || '8080', 10);
const budget = parseFloat(process.env.BUDGET || '5.0');

console.log(`[TokenWall] Initializing Firewall Database...`);
console.log(`[TokenWall] Active Budget: $${budget.toFixed(2)}/day`);

start(port);
