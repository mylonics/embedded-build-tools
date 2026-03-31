#!/usr/bin/env node
/**
 * Embedded Build Tools — Node.js Installer
 *
 * Downloads and extracts the correct pre-built release for your platform.
 * Zero dependencies — uses only Node.js built-ins.
 *
 * Usage:
 *   node install.js
 *   node install.js --version v1.0.0 --dest ./my-tools
 *   node install.js --platform linux-arm64
 */

const https = require("https");
const http = require("http");
const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const REPO = "mylonics/embedded-build-tools";

// ── Platform detection ──────────────────────────────────────────────────────

function detectPlatform() {
  const osMap = { win32: "win32", linux: "linux", darwin: "darwin" };
  const archMap = { x64: "x64", arm64: "arm64" };

  const osName = osMap[os.platform()];
  const archName = archMap[os.arch()];

  if (!osName || !archName) {
    console.error(`Error: Unsupported platform: ${os.platform()}-${os.arch()}`);
    process.exit(1);
  }

  return `${osName}-${archName}`;
}

// ── HTTP download (follows redirects) ───────────────────────────────────────

function download(url, destPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    const proto = url.startsWith("https") ? https : http;

    function doRequest(requestUrl) {
      proto
        .get(requestUrl, { headers: { "User-Agent": "embedded-build-tools-installer" } }, (res) => {
          // Follow redirects (302, 301)
          if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            file.close();
            fs.unlinkSync(destPath);
            // GitHub redirects to a different host, so we need to handle http vs https
            const loc = res.headers.location;
            const nextProto = loc.startsWith("https") ? https : http;
            nextProto
              .get(loc, { headers: { "User-Agent": "embedded-build-tools-installer" } }, (res2) => {
                if (res2.statusCode !== 200) {
                  reject(new Error(`Download failed: HTTP ${res2.statusCode}`));
                  return;
                }
                const totalBytes = parseInt(res2.headers["content-length"] || "0", 10);
                let downloaded = 0;
                const newFile = fs.createWriteStream(destPath);

                res2.on("data", (chunk) => {
                  downloaded += chunk.length;
                  if (totalBytes > 0) {
                    const pct = Math.min(100, Math.floor((downloaded / totalBytes) * 100));
                    const mbDown = (downloaded / (1024 * 1024)).toFixed(1);
                    const mbTotal = (totalBytes / (1024 * 1024)).toFixed(1);
                    process.stdout.write(`\r  Progress: ${pct}% (${mbDown}/${mbTotal} MB)`);
                  }
                });

                res2.pipe(newFile);
                newFile.on("finish", () => {
                  newFile.close();
                  console.log();
                  resolve();
                });
                newFile.on("error", reject);
              })
              .on("error", reject);
            return;
          }

          if (res.statusCode !== 200) {
            file.close();
            fs.unlinkSync(destPath);
            reject(new Error(`Download failed: HTTP ${res.statusCode}`));
            return;
          }

          const totalBytes = parseInt(res.headers["content-length"] || "0", 10);
          let downloaded = 0;

          res.on("data", (chunk) => {
            downloaded += chunk.length;
            if (totalBytes > 0) {
              const pct = Math.min(100, Math.floor((downloaded / totalBytes) * 100));
              const mbDown = (downloaded / (1024 * 1024)).toFixed(1);
              const mbTotal = (totalBytes / (1024 * 1024)).toFixed(1);
              process.stdout.write(`\r  Progress: ${pct}% (${mbDown}/${mbTotal} MB)`);
            }
          });

          res.pipe(file);
          file.on("finish", () => {
            file.close();
            console.log();
            resolve();
          });
          file.on("error", reject);
        })
        .on("error", (err) => {
          file.close();
          fs.unlinkSync(destPath);
          reject(err);
        });
    }

    doRequest(url);
  });
}

// ── Extraction ──────────────────────────────────────────────────────────────

function extractArchive(archivePath, destDir) {
  fs.mkdirSync(destDir, { recursive: true });

  if (archivePath.endsWith(".zip")) {
    // Use PowerShell on Windows, unzip on Unix
    if (os.platform() === "win32") {
      execSync(
        `powershell -NoProfile -Command "Expand-Archive -Path '${archivePath}' -DestinationPath '${destDir}' -Force"`,
        { stdio: "inherit" }
      );
    } else {
      execSync(`unzip -qo "${archivePath}" -d "${destDir}"`, { stdio: "inherit" });
    }
  } else {
    // tar.gz
    execSync(`tar xzf "${archivePath}" -C "${destDir}"`, { stdio: "inherit" });
  }
}

// ── macOS quarantine removal ────────────────────────────────────────────────

function removeQuarantine(dir) {
  if (os.platform() !== "darwin") return;
  console.log("Removing macOS quarantine attributes...");
  try {
    execSync(`xattr -cr "${dir}"`, { stdio: "ignore" });
  } catch {
    // Ignore errors
  }
}

// ── Argument parsing ────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { version: "latest", dest: "embedded-build-tools", platform: null };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--version":
      case "-v":
        opts.version = args[++i];
        break;
      case "--dest":
      case "-d":
        opts.dest = args[++i];
        break;
      case "--platform":
      case "-p":
        opts.platform = args[++i];
        break;
      case "--help":
      case "-h":
        console.log("Usage: node install.js [options]");
        console.log("");
        console.log("Options:");
        console.log("  --version, -v <tag>   GitHub release tag (default: latest)");
        console.log("  --dest, -d <dir>      Destination directory (default: ./embedded-build-tools)");
        console.log("  --platform, -p <plat> Override platform (e.g., linux-x64, darwin-arm64)");
        process.exit(0);
      default:
        console.error(`Unknown option: ${args[i]}`);
        process.exit(1);
    }
  }

  return opts;
}

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  const opts = parseArgs();
  const plat = opts.platform || detectPlatform();
  const isWindows = plat.startsWith("win32");

  const artifact = isWindows
    ? `embedded-build-tools-${plat}.zip`
    : `embedded-build-tools-${plat}.tar.gz`;

  const url =
    opts.version === "latest"
      ? `https://github.com/${REPO}/releases/latest/download/${artifact}`
      : `https://github.com/${REPO}/releases/download/${opts.version}/${artifact}`;

  console.log(`Platform:    ${plat}`);
  console.log(`Version:     ${opts.version}`);
  console.log(`Artifact:    ${artifact}`);
  console.log(`Destination: ${opts.dest}`);
  console.log();

  // Download to temp file
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "ebt-"));
  const tmpFile = path.join(tmpDir, artifact);

  try {
    console.log(`Downloading: ${url}`);
    await download(url, tmpFile);

    console.log(`Extracting to: ${opts.dest}`);
    extractArchive(tmpFile, opts.dest);

    removeQuarantine(opts.dest);

    console.log();
    console.log(`Embedded build tools installed to: ${opts.dest}`);
    console.log();
    if (isWindows) {
      console.log("Next steps:");
      console.log(`  cd ${opts.dest}`);
      console.log("  call env.bat        (cmd)");
      console.log("  . .\\env.ps1         (PowerShell)");
    } else {
      console.log("Next steps:");
      console.log(`  cd ${opts.dest}`);
      console.log("  source env.sh");
    }
    console.log();
  } finally {
    // Clean up temp
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // Ignore
    }
  }
}

main().catch((err) => {
  console.error(`Error: ${err.message}`);
  process.exit(1);
});
