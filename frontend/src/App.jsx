import { useEffect, useState } from "react";
import { get, post } from "./api.js";

const COLORS = ["#4f46e5", "#16a34a", "#ea580c"];

export default function App() {
  const [gateways, setGateways] = useState([]);
  const [stats, setStats] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [count, setCount] = useState(100);
  const [running, setRunning] = useState(false);

  async function refresh() {
    const [g, s, t] = await Promise.all([get("/gateways"), get("/stats"), get("/transactions")]);
    setGateways(g);
    setStats(s);
    setTransactions(t);
  }

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, []);

  async function toggleDegrade(id) {
    await post(`/gateways/${id}/degrade`);
    refresh();
  }

  async function simulate() {
    setRunning(true);
    await post(`/simulate?count=${count}`);
    setRunning(false);
    refresh();
  }

  return (
    <main>
      <h1>Smart Payment Routing Engine</h1>

      <section>
        <h2>Gateways</h2>
        <table>
          <thead>
            <tr><th>Name</th><th>Fee</th><th>Avg latency</th><th>Success rate</th><th>Score</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {gateways.map((g) => (
              <tr key={g.id}>
                <td>{g.name}</td>
                <td>{g.fee_pct}%</td>
                <td>{g.avg_latency_ms} ms</td>
                <td>{(g.success_rate * 100).toFixed(1)}%</td>
                <td>{g.score}</td>
                <td className={g.degraded ? "bad" : "good"}>{g.degraded ? "Degraded" : "Healthy"}</td>
                <td><button onClick={() => toggleDegrade(g.id)}>{g.degraded ? "Restore" : "Degrade"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {stats && (
        <section>
          <h2>Stats</h2>
          <div className="stats">
            <div><strong>{stats.total_transactions}</strong>transactions</div>
            <div><strong>{(stats.success_rate * 100).toFixed(1)}%</strong>success rate</div>
            <div><strong>{stats.avg_attempts}</strong>avg attempts</div>
          </div>
          <div className="bar">
            {Object.entries(stats.traffic_share).map(([name, share], i) => (
              <div key={name} title={name} style={{ width: `${share * 100}%`, background: COLORS[i % COLORS.length] }}>
                {share > 0.08 && `${name} ${(share * 100).toFixed(0)}%`}
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2>Simulate</h2>
        <input type="number" min="1" value={count} onChange={(e) => setCount(Number(e.target.value))} />
        <button onClick={simulate} disabled={running}>{running ? "Running..." : "Run simulation"}</button>
      </section>

      <section>
        <h2>Latest transactions</h2>
        <table>
          <thead>
            <tr><th>ID</th><th>Amount</th><th>Status</th><th>Attempts</th></tr>
          </thead>
          <tbody>
            {transactions.map((t) => (
              <tr key={t.id}>
                <td>{t.id}</td>
                <td>{t.amount.toFixed(2)}</td>
                <td className={t.status === "succeeded" ? "good" : "bad"}>{t.status}</td>
                <td>{t.attempts.map((a) => `${a.gateway} ${a.success ? "succeeded" : "failed"}`).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
