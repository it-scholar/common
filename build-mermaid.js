const path = require("path");
const { exec } = require("child_process");

const inputFile = process.argv[2];
// Optional explicit output path (.svg or .pdf). Defaults to an .svg next to
// the input. PDF output is page-fitted (--pdfFit) so it can be dropped into
// \includegraphics directly.
const outputFile = process.argv[3];

if (!inputFile || !inputFile.endsWith(".mmd")) {
  console.error("Only .mmd files are supported.");
  process.exit(1);
}

if (outputFile && !/\.(svg|pdf)$/.test(outputFile)) {
  console.error("Output file must end in .svg or .pdf");
  process.exit(1);
}

const absInput = path.resolve(inputFile);
const absOutput = outputFile
  ? path.resolve(outputFile)
  : absInput.replace(/\.mmd$/, ".svg");
const configFile = path.resolve("common/puppeteer-config.json");
const mmdc = path.resolve("common/node_modules/.bin/mmdc");

const pdfFit = absOutput.endsWith(".pdf") ? " --pdfFit" : "";
const cmd = `"${mmdc}" -i "${absInput}" -o "${absOutput}"${pdfFit} --puppeteerConfigFile "${configFile}"`;

console.log("Running command:", cmd);

exec(cmd, (err, stdout, stderr) => {
  if (err) {
    console.error("❌ Mermaid CLI error:", stderr || err.message);
    process.exit(1);
  } else {
    console.log(`✅ Built ${absOutput}`);
  }
});
