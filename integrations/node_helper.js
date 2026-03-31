/**
 * Embedded Build Tools — Node.js / Electron Integration Helper
 *
 * Zero-dependency module for locating embedded build tools from
 * Node.js or Electron applications.
 *
 * Usage:
 *   const { EmbeddedToolchain } = require('./integrations/node_helper');
 *   const tc = new EmbeddedToolchain('/path/to/embedded-build-tools');
 *   const gcc = tc.gccPath();
 *   const env = tc.getEnv();
 */

const path = require("path");
const fs = require("fs");
const os = require("os");

class EmbeddedToolchain {
  /**
   * @param {string} rootDir - Path to the embedded-build-tools directory
   * @param {string} [platform] - Override platform detection (e.g. 'win32-x64')
   */
  constructor(rootDir, platform) {
    this.root = path.resolve(rootDir);
    this.toolsDir = path.join(this.root, "tools");
    this.platform = platform || this._detectPlatform();
    this._isWindows = this.platform.startsWith("win32");
    this._ext = this._isWindows ? ".exe" : "";

    // Load manifest
    const manifestPath = path.join(this.root, "tool-manifest.json");
    if (fs.existsSync(manifestPath)) {
      this._manifest = JSON.parse(
        fs.readFileSync(manifestPath, "utf-8")
      );
    } else {
      this._manifest = {};
    }
  }

  _detectPlatform() {
    const osMap = { win32: "win32", linux: "linux", darwin: "darwin" };
    const archMap = { x64: "x64", arm64: "arm64" };
    const osName = osMap[os.platform()] || os.platform();
    const archName = archMap[os.arch()] || os.arch();
    return `${osName}-${archName}`;
  }

  _exists(p) {
    return fs.existsSync(p) ? p : null;
  }

  // ── Individual tool paths ───────────────────────────────────────────

  /** @returns {string|null} Path to arm-none-eabi-gcc */
  gccPath() {
    return this._exists(
      path.join(this.toolsDir, "arm-none-eabi-gcc", "bin", `arm-none-eabi-gcc${this._ext}`)
    );
  }

  /** @returns {string|null} Path to arm-none-eabi-g++ */
  gppPath() {
    return this._exists(
      path.join(this.toolsDir, "arm-none-eabi-gcc", "bin", `arm-none-eabi-g++${this._ext}`)
    );
  }

  /** @returns {string|null} Path to arm-none-eabi-gdb */
  gdbPath() {
    return this._exists(
      path.join(this.toolsDir, "arm-none-eabi-gcc", "bin", `arm-none-eabi-gdb${this._ext}`)
    );
  }

  /** @returns {string|null} Path to cmake */
  cmakePath() {
    return this._exists(
      path.join(this.toolsDir, "cmake", "bin", `cmake${this._ext}`)
    );
  }

  /** @returns {string|null} Path to ninja */
  ninjaPath() {
    return this._exists(
      path.join(this.toolsDir, "ninja-build", "bin", `ninja${this._ext}`)
    );
  }

  /** @returns {string|null} Path to portable python */
  pythonPath() {
    if (this._isWindows) {
      const p = path.join(this.toolsDir, "python", "python", `python${this._ext}`);
      if (fs.existsSync(p)) return p;
    }
    return this._exists(
      path.join(this.toolsDir, "python", "bin", `python3${this._ext}`)
    );
  }

  /** @returns {string|null} Path to arm-none-eabi-objcopy */
  objcopyPath() {
    return this._exists(
      path.join(this.toolsDir, "arm-none-eabi-gcc", "bin", `arm-none-eabi-objcopy${this._ext}`)
    );
  }

  /** @returns {string|null} Path to arm-none-eabi-size */
  sizePath() {
    return this._exists(
      path.join(this.toolsDir, "arm-none-eabi-gcc", "bin", `arm-none-eabi-size${this._ext}`)
    );
  }

  // ── Directories ─────────────────────────────────────────────────────

  /** @returns {string[]} List of bin directories that exist */
  binDirs() {
    const candidates = [
      path.join(this.toolsDir, "arm-none-eabi-gcc", "bin"),
      path.join(this.toolsDir, "cmake", "bin"),
      path.join(this.toolsDir, "ninja-build", "bin"),
      this._isWindows
        ? path.join(this.toolsDir, "python", "python")
        : path.join(this.toolsDir, "python", "bin"),
    ];
    return candidates.filter((d) => fs.existsSync(d));
  }

  // ── Environment ─────────────────────────────────────────────────────

  /**
   * Get PATH string with tool directories prepended.
   * @param {boolean} [includeSystem=true] - Include system PATH
   * @returns {string}
   */
  pathString(includeSystem = true) {
    const sep = this._isWindows ? ";" : ":";
    const toolPaths = this.binDirs().join(sep);
    if (includeSystem) {
      const systemPath = process.env.PATH || "";
      return toolPaths ? `${toolPaths}${sep}${systemPath}` : systemPath;
    }
    return toolPaths;
  }

  /**
   * Get environment object suitable for child_process.spawn(cmd, args, { env }).
   * @param {boolean} [inherit=true] - Inherit current process.env
   * @returns {Object.<string, string>}
   */
  getEnv(inherit = true) {
    const env = inherit ? { ...process.env } : {};
    env.PATH = this.pathString(inherit);

    const gcc = this.gccPath();
    if (gcc) {
      env.ARM_GCC = gcc;
      env.ARM_GCC_DIR = path.dirname(path.dirname(gcc));
    }

    const gdb = this.gdbPath();
    if (gdb) env.ARM_GDB = gdb;

    const cmake = this.cmakePath();
    if (cmake) env.CMAKE = cmake;

    const ninja = this.ninjaPath();
    if (ninja) env.NINJA = ninja;

    const python = this.pythonPath();
    if (python) env.PYTHON = python;

    return env;
  }

  /**
   * Get installed versions from .version stamp files.
   * @returns {Object.<string, string>}
   */
  versions() {
    const result = {};
    for (const tool of ["arm-none-eabi-gcc", "cmake", "ninja-build", "python"]) {
      const stamp = path.join(this.toolsDir, tool, ".version");
      if (fs.existsSync(stamp)) {
        result[tool] = fs.readFileSync(stamp, "utf-8").trim();
      }
    }
    return result;
  }

  /**
   * Check if all tools are installed.
   * @returns {boolean}
   */
  isComplete() {
    return !!(this.gccPath() && this.cmakePath() && this.ninjaPath());
  }

  /**
   * Serialize to a plain object with all paths and versions.
   * @returns {Object}
   */
  toJSON() {
    return {
      platform: this.platform,
      root: this.root,
      toolsDir: this.toolsDir,
      versions: this.versions(),
      complete: this.isComplete(),
      paths: {
        gcc: this.gccPath(),
        "g++": this.gppPath(),
        gdb: this.gdbPath(),
        objcopy: this.objcopyPath(),
        size: this.sizePath(),
        cmake: this.cmakePath(),
        ninja: this.ninjaPath(),
        python: this.pythonPath(),
      },
      binDirs: this.binDirs(),
    };
  }
}

module.exports = { EmbeddedToolchain };
