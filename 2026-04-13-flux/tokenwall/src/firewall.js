const db = require('./db');
const DAILY_BUDGET = parseFloat(process.env.BUDGET || '5.0');

/**
 * Checks if the total cost for the current day is under the allocated budget.
 */
function isUnderBudget() {
    const stmt = db.prepare(`SELECT COALESCE(SUM(cost), 0.0) as total FROM usage WHERE date(timestamp) = date('now')`);
    const row = stmt.get();
    return row.total < DAILY_BUDGET;
}

/**
 * Records the exact computed cost of a transaction.
 */
function recordUsage(cost) {
    const stmt = db.prepare(`INSERT INTO usage (cost) VALUES (?)`);
    stmt.run(cost);
}

module.exports = { isUnderBudget, recordUsage };
