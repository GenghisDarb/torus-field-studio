import { readdir, stat } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const distribution = path.join(root, "apps", "studio", "dist");
const limits = {
  application: 950 * 1024,
  publishedExamples: 1024 * 1024,
  mainJavaScript: 450 * 1024,
  surfaceJavaScript: 650 * 1024,
  css: 120 * 1024,
};

async function filesBelow(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? filesBelow(target) : [target];
  }));
  return nested.flat();
}

const files = await filesBelow(distribution);
const sizes = await Promise.all(files.map(async (file) => ({ file, bytes: (await stat(file)).size })));
const application = sizes.filter(({ file }) => !file.endsWith(".map") && !file.includes(`${path.sep}examples${path.sep}`)).reduce((sum, item) => sum + item.bytes, 0);
const publishedExamples = sizes.filter(({ file }) => file.includes(`${path.sep}examples${path.sep}`)).reduce((sum, item) => sum + item.bytes, 0);
const mainJavaScript = Math.max(0, ...sizes.filter(({ file }) => /assets[\\/]index-.*\.js$/.test(file)).map(({ bytes }) => bytes));
const surfaceJavaScript = Math.max(0, ...sizes.filter(({ file }) => /assets[\\/]Surface3D-.*\.js$/.test(file)).map(({ bytes }) => bytes));
const css = sizes.filter(({ file }) => file.endsWith(".css")).reduce((sum, item) => sum + item.bytes, 0);
const measurements = { application, publishedExamples, mainJavaScript, surfaceJavaScript, css };
const failures = Object.entries(measurements).filter(([name, bytes]) => bytes > limits[name]);
for (const [name, bytes] of Object.entries(measurements)) console.log(`${name}: ${bytes} / ${limits[name]} bytes`);
if (failures.length) {
  console.error(`Bundle budget exceeded: ${failures.map(([name]) => name).join(", ")}`);
  process.exitCode = 1;
}
