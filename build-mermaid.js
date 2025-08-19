const path = require("path");
const { exec } = require("child_process");

const inputFile = process.argv[2];

if (!inputFile || !inputFile.endsWith(".mmd")) {
  console.error("Only .mmd files are supported.");
  process.exit(1);
}

const absInput = path.resolve(inputFile);
const absOutput = absInput.replace(/\.mmd$/, ".svg");
const configFile = path.resolve("common/puppeteer-config.json");

const cmd = `npx -y @mermaid-js/mermaid-cli -i "${absInput}" -o "${absOutput}" --puppeteerConfigFile "${configFile}"`;

console.log("Running command:", cmd);

exec(cmd, (err, stdout, stderr) => {
  if (err) {
    console.error("❌ Mermaid CLI error:", stderr || err.message);
    process.exit(1);
  } else {
    console.log(`✅ Built ${absOutput}`);
  }
});
