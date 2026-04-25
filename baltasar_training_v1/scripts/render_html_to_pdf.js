const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

async function main() {
  const htmlPath = process.argv[2];
  const pdfPath = process.argv[3];
  if (!htmlPath || !pdfPath) {
    throw new Error("Usage: node render_html_to_pdf.js <htmlPath> <pdfPath>");
  }

  const launchOptions = { headless: true };
  if (process.env.PW_EXECUTABLE_PATH) {
    launchOptions.executablePath = process.env.PW_EXECUTABLE_PATH;
  }
  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({
    viewport: { width: 1400, height: 2000 },
    deviceScaleFactor: 1.25,
  });

  const url = pathToFileURL(path.resolve(htmlPath)).href;
  await page.goto(url, { waitUntil: "networkidle" });
  await page.evaluate(async () => {
    const images = Array.from(document.images);
    await Promise.all(images.map((img) => {
      if (img.complete) return Promise.resolve();
      return new Promise((resolve) => {
        img.addEventListener("load", resolve, { once: true });
        img.addEventListener("error", resolve, { once: true });
      });
    }));
    await document.fonts.ready;
  });

  await page.pdf({
    path: path.resolve(pdfPath),
    format: "A4",
    printBackground: true,
    margin: { top: "8mm", right: "8mm", bottom: "8mm", left: "8mm" },
    preferCSSPageSize: true,
  });

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
