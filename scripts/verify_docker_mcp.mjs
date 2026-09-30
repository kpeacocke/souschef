#!/usr/bin/env node
// Exercise the actual container's MCP stdio protocol without application mocks.
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { chmod, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createInterface } from "node:readline";

const image = process.argv[2] ?? "mcp/souschef";
const gatewayCatalog = process.argv[3];
const gatewayMode = Boolean(gatewayCatalog);
const workspace = await mkdtemp(path.join(tmpdir(), "souschef-mcp-"));
const containerName = `souschef-verify-${randomUUID()}`;
const recipePath = path.join(workspace, "cookbooks", "web", "recipes", "default.rb");
await mkdir(path.dirname(recipePath), { recursive: true });
await writeFile(recipePath, "package 'nginx' do\n  action :install\nend\n");
await chmod(workspace, 0o755);
const pending = new Map();
let requestId = 0;
let stderr = "";
const directArgs = [
  "run", "--rm", "-i", "--init", "--name", containerName,
  "--cap-drop=ALL", "--security-opt=no-new-privileges", "--network=none",
  "--env", "SOUSCHEF_WORKSPACE_ROOT=/workspace",
  "--mount", `type=bind,source=${workspace},target=/workspace`,
  image,
];
const configPath = path.join(workspace, "gateway-config.yaml");
const secretsPath = path.join(workspace, "empty.env");
if (gatewayMode) {
  await writeFile(configPath, JSON.stringify({ souschef: { workspace } }));
  await writeFile(secretsPath, "");
}
const gatewayArgs = [
  "mcp", "gateway", "run", "--servers", "souschef",
  "--catalog", path.resolve(gatewayCatalog ?? "."),
  "--config", configPath, "--secrets", secretsPath,
  "--verify-signatures=false", "--watch=false", "--log-calls=false",
];
const server = spawn("docker", gatewayMode ? gatewayArgs : directArgs,
  { stdio: ["pipe", "pipe", "pipe"] });
server.stderr.setEncoding("utf8");
server.stderr.on("data", chunk => { stderr = (stderr + chunk).slice(-16000); });
function rejectPending(error) {
  for (const { reject, timer } of pending.values()) {
    clearTimeout(timer);
    reject(error);
  }
  pending.clear();
}
server.on("error", rejectPending);
server.on("exit", (code, signal) => {
  rejectPending(new Error(`MCP container exited: ${code ?? signal}\n${stderr}`));
});
const lines = createInterface({ input: server.stdout });
lines.on("line", line => {
  let message;
  try { message = JSON.parse(line); }
  catch { rejectPending(new Error(`Non-JSON output on MCP stdout: ${line}`)); return; }
  if (message.id == null) return;
  const waiting = pending.get(message.id);
  if (!waiting) return;
  pending.delete(message.id);
  clearTimeout(waiting.timer);
  if (message.error) waiting.reject(new Error(JSON.stringify(message.error)));
  else waiting.resolve(message.result);
});
function request(method, params) {
  const id = ++requestId;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Timed out waiting for ${method}\n${stderr}`));
    }, 60000);
    pending.set(id, { resolve, reject, timer });
    server.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n",
      error => { if (error) rejectPending(error); });
  });
}
function textContent(result) {
  return (result.content ?? []).filter(item => item.type === "text")
    .map(item => item.text).join("\n");
}
const toolNames = new Map();
async function call(name, args) {
  name = toolNames.get(name) ?? name;
  const result = await request("tools/call", { name, arguments: args });
  assert.equal(result.isError ?? false, false, `${name}: ${textContent(result)}`);
  return textContent(result);
}

try {
  const init = await request("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "souschef-container-verification", version: "1.0.0" },
  });
  assert.ok(init.capabilities.tools, "Server must advertise tool support");
  server.stdin.write(JSON.stringify({
    jsonrpc: "2.0", method: "notifications/initialized",
  }) + "\n");
  const tools = [];
  let cursor;
  do {
    const page = await request("tools/list", cursor ? { cursor } : {});
    tools.push(...page.tools);
    cursor = page.nextCursor;
  } while (cursor);
  for (const name of ["parse_recipe", "read_file", "convert_resource_to_task"]) {
    const matches = tools.filter(tool => tool.name === name ||
      tool.name.endsWith(`__${name}`) || tool.name.endsWith(`_${name}`));
    assert.equal(matches.length, 1, `Missing or ambiguous tool: ${name}`);
    toolNames.set(name, matches[0].name);
  }
  console.log(`PASS: MCP initialise and discovery (${tools.length} tools)`);

  const recipe = await call("read_file", {
    path: "/workspace/cookbooks/web/recipes/default.rb",
  });
  assert.equal(recipe.trim(), (await readFile(recipePath, "utf8")).trim());
  console.log("PASS: read_file reads the host-mounted fixture");

  const parsed = await call("parse_recipe", {
    path: "/workspace/cookbooks/web/recipes/default.rb",
  });
  assert.match(parsed, /nginx/);
  assert.match(parsed, /package/);
  assert.match(parsed, /install/);
  assert.doesNotMatch(parsed, /^Error:/m);
  console.log("PASS: parse_recipe extracts package[nginx], action install");

  const converted = await call("convert_resource_to_task", {
    resource_type: "package", resource_name: "nginx", action: "install",
  });
  assert.match(converted, /ansible\.builtin\.package/);
  assert.match(converted, /name:\s*nginx/);
  assert.match(converted, /state:\s*present/);
  console.log("PASS: conversion produces ansible.builtin.package, nginx, present");
  console.log(converted);

  for (const attemptedPath of ["/etc/passwd", "/workspace/../etc/passwd"]) {
    const result = await request("tools/call", {
      name: toolNames.get("read_file"), arguments: { path: attemptedPath },
    });
    const rejected = textContent(result);
    assert.ok(result.isError || /error|escapes|outside|traversal/i.test(rejected),
      `Out-of-workspace path was not rejected: ${attemptedPath}`);
    assert.doesNotMatch(rejected, /^root:[^\n]*:/m);
  }
  console.log("PASS: absolute and traversal paths outside /workspace are rejected");
  console.log(gatewayMode ? "PASS: generated catalogue works through Docker MCP Gateway" :
    "PASS: no credentials or outbound container network required");
} finally {
  lines.close();
  server.stdin.end();
  if (!gatewayMode) {
    spawnSync("docker", ["rm", "-f", containerName], { stdio: "ignore", timeout: 15000 });
  }
  server.kill();
  rejectPending(new Error("Verification finished"));
  await rm(workspace, { recursive: true, force: true });
}
