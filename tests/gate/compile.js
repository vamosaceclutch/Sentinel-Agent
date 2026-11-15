// Compile SentinelRegistry.sol + AuditGate.sol with the same compiler as Remix (0.8.24).
// Usage: node compile.js <evm: shanghai|paris> [path/to/SentinelRegistry.sol] [path/to/AuditGate.sol]
const solc = require("solc");
const fs = require("fs");
const path = require("path");
const evm = process.argv[2] || "shanghai";
const root = path.resolve(__dirname, "..", "..");
const files = {
  "SentinelRegistry.sol": process.argv[3] || path.join(root, "SentinelRegistry.sol"),
  "AuditGate.sol": process.argv[4] || path.join(root, "AuditGate.sol"),
};
const sources = {};
for (const [k, v] of Object.entries(files)) sources[k] = { content: fs.readFileSync(v, "utf8") };
const input = {
  language: "Solidity", sources,
  settings: { evmVersion: evm, optimizer: { enabled: false }, outputSelection: { "*": { "*": ["abi", "evm.bytecode.object"] } } },
};
const out = JSON.parse(solc.compile(JSON.stringify(input)));
let bad = false;
for (const e of out.errors || []) {
  console.error(e.severity.toUpperCase() + ": " + e.formattedMessage.split("\n")[0]);
  if (e.severity === "error") bad = true;
}
if (bad) process.exit(1);
const res = {};
for (const cs of Object.values(out.contracts))
  for (const [name, c] of Object.entries(cs)) res[name] = { abi: c.abi, bin: c.evm.bytecode.object };
fs.writeFileSync(path.join(__dirname, `compiled_${evm}.json`), JSON.stringify(res));
console.log("compiled:", Object.keys(res).join(", "), "evm=" + evm);
