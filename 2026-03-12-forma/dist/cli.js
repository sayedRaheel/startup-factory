"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// src/cli.ts
var import_commander = require("commander");

// src/parser/index.ts
var import_fs = require("fs");
function parseFormaFile(filePath) {
  const content = (0, import_fs.readFileSync)(filePath, "utf-8");
  const systemMatch = content.match(/system:\s*"?([^"\n]+)"?/);
  const modelMatch = content.match(/model:\s*"?([^"\n]+)"?/);
  if (!systemMatch) throw new Error("Syntax Error: Missing 'system' directive.");
  const ast = {
    system: systemMatch[1],
    model: modelMatch ? modelMatch[1] : "gpt-4o",
    input: {},
    output: {}
  };
  const inputBlock = content.match(/input\s*{([^}]+)}/);
  if (inputBlock) {
    const lines = inputBlock[1].split("\n");
    for (const line of lines) {
      const match = line.match(/^\s*([a-zA-Z0-9_]+)\s*:\s*([a-zA-Z0-9_]+)/);
      if (match) {
        ast.input[match[1]] = match[2];
      }
    }
  }
  const outputBlock = content.match(/output\s*{([^}]+)}/);
  if (outputBlock) {
    const lines = outputBlock[1].split("\n");
    for (const line of lines) {
      const match = line.match(/^\s*([a-zA-Z0-9_]+)\s*:\s*([a-zA-Z0-9_]+)/);
      if (match) {
        ast.output[match[1]] = match[2];
      }
    }
  }
  return ast;
}

// src/compiler/index.ts
function compileToPayload(ast) {
  const properties = {};
  for (const [key, type] of Object.entries(ast.output)) {
    let jsonType = "string";
    if (type === "number") jsonType = "number";
    if (type === "boolean") jsonType = "boolean";
    if (type === "object") jsonType = "object";
    properties[key] = { type: jsonType };
  }
  const jsonSchema = {
    type: "json_schema",
    json_schema: {
      name: "forma_output",
      schema: {
        type: "object",
        properties,
        required: Object.keys(ast.output),
        additionalProperties: false
      },
      strict: true
    }
  };
  return {
    model: ast.model || "gpt-4o",
    messages: [
      { role: "system", content: ast.system }
    ],
    response_format: jsonSchema
  };
}

// src/runner/index.ts
var import_openai = __toESM(require("openai"));
var import_dotenv = __toESM(require("dotenv"));
import_dotenv.default.config();
async function runTest(filePath, mockInput) {
  const ast = parseFormaFile(filePath);
  const payload = compileToPayload(ast);
  if (!process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is not set.");
  }
  const openai = new import_openai.default();
  const messages = [
    ...payload.messages,
    { role: "user", content: mockInput }
  ];
  const response = await openai.chat.completions.create({
    model: payload.model,
    messages,
    response_format: payload.response_format
  });
  return response.choices[0].message.content;
}

// src/cli.ts
var import_fs2 = require("fs");
var program = new import_commander.Command();
program.name("forma").description("Forma CLI - Compile strongly typed LLM prompts").version("1.0.0");
program.command("build").description("Compile a .forma file into an API payload").argument("<file>", "Path to the .forma file").action((file) => {
  try {
    console.log(`Analyzing ${file}...`);
    const ast = parseFormaFile(file);
    const payload = compileToPayload(ast);
    const outFile = file.replace(".forma", ".json");
    (0, import_fs2.writeFileSync)(outFile, JSON.stringify(payload, null, 2));
    console.log(`\u2705 Successfully compiled to ${outFile}`);
  } catch (error) {
    console.error(`\u274C Build failed: ${error.message}`);
    process.exit(1);
  }
});
program.command("test").description("Execute a .forma file against an LLM and assert outputs").argument("<file>", "Path to the .forma file").argument("<input>", "Mock input string to feed to the LLM").action(async (file, input) => {
  try {
    console.log(`Executing ${file} with input: "${input}"...`);
    const result = await runTest(file, input);
    console.log(`\u2705 Execution Success:
${result}`);
  } catch (error) {
    console.error(`\u274C Execution failed: ${error.message}`);
    process.exit(1);
  }
});
program.parse();
