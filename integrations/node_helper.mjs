/**
 * Embedded Build Tools — Node.js ESM Integration Helper
 *
 * ESM wrapper around node_helper.js for use with ES module imports.
 *
 * Usage:
 *   import { EmbeddedToolchain } from './integrations/node_helper.mjs';
 *   const tc = new EmbeddedToolchain('/path/to/embedded-build-tools');
 *   const gcc = tc.gccPath();
 *   const env = tc.getEnv();
 */

import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { EmbeddedToolchain } = require("./node_helper.js");

export { EmbeddedToolchain };
export default EmbeddedToolchain;
