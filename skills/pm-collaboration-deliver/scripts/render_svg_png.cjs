#!/usr/bin/env node
"use strict";

const path = require("path");
const fs = require("fs");
const { spawnSync } = require("child_process");

if (process.argv.length !== 4) {
  console.error("usage: render_svg_png.cjs input.svg output.png");
  process.exit(2);
}

let sharp;
try {
  sharp = require("sharp");
} catch (firstError) {
  sharp = null;
  if (process.env.NODE_PATH) {
    try {
      sharp = require(path.join(process.env.NODE_PATH, "sharp"));
    } catch (secondError) {
      sharp = null;
    }
  }
}

const input = process.argv[2];
const output = process.argv[3];

if (sharp) {
  sharp(input, { density: 144 })
    .png()
    .toFile(output)
    .then(() => process.exit(0))
    .catch((error) => {
      console.error(error.message);
      process.exit(2);
    });
} else {
  const candidates = process.platform === "darwin"
    ? [["/usr/bin/sips", ["-s", "format", "png", input, "--out", output]]]
    : [
        ["rsvg-convert", ["-o", output, input]],
        ["inkscape", [input, "--export-type=png", `--export-filename=${output}`]],
      ];

  let lastError = "sharp is unavailable and no native SVG renderer succeeded";
  for (const [command, args] of candidates) {
    const result = spawnSync(command, args, { encoding: "utf8" });
    if (result.status === 0 && fs.existsSync(output) && fs.statSync(output).size > 0) {
      process.exit(0);
    }
    if (result.error || result.stderr) {
      lastError = String(result.error?.message || result.stderr).trim();
    }
  }
  console.error(lastError);
  process.exit(2);
}
