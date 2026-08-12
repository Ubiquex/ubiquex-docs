// UBI-144 Phase 2: per-tab overflow crawl -- UBI-148's own crawl.js
// only measured whichever tab happens to be active by default (Go).
// This clicks through Go/TypeScript/Python/Markdown for each page and
// measures pre.scrollWidth vs clientWidth for the tab that's actually
// visible after each click, same methodology as every session tonight.
//
// Usage: node crawl_tabs.js <pages-file> <base-url> <out-jsonl> <concurrency>

const { chromium } = require('playwright');
const fs = require('fs');

async function main() {
  const [pagesFile, baseUrl, outFile, concurrencyArg] = process.argv.slice(2);
  const concurrency = parseInt(concurrencyArg || '4', 10);
  const pages = fs.readFileSync(pagesFile, 'utf8').split('\n').map(l => l.trim()).filter(Boolean);

  const out = fs.createWriteStream(outFile, { flags: 'a' });
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  let idx = 0, done = 0;
  const total = pages.length;
  const startTime = Date.now();

  async function measureActiveTab(page) {
    return page.evaluate(() => {
      const doc = { scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth };
      const pre = [...document.querySelectorAll('main pre')].find(el => el.clientWidth > 0);
      if (!pre) return { doc, pageOverflowPx: doc.scrollWidth - doc.clientWidth, pre: null };
      let ancestor = pre.parentElement, scrollAncestorFound = false;
      for (let i = 0; i < 6 && ancestor; i++) {
        const cs = getComputedStyle(ancestor);
        if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') { scrollAncestorFound = true; break; }
        ancestor = ancestor.parentElement;
      }
      return {
        doc,
        pageOverflowPx: doc.scrollWidth - doc.clientWidth,
        pre: {
          scrollWidth: pre.scrollWidth, clientWidth: pre.clientWidth,
          overflowPx: pre.scrollWidth - pre.clientWidth,
          contained: scrollAncestorFound,
        },
      };
    });
  }

  async function worker() {
    const page = await context.newPage();
    while (idx < pages.length) {
      const myIdx = idx++;
      const path = pages[myIdx];
      const url = baseUrl.replace(/\/$/, '') + '/' + path.replace(/^\//, '');
      let result = { path, tabs: {}, error: null };
      try {
        await page.goto(url, { waitUntil: 'load', timeout: 20000 });
        await page.waitForTimeout(200);

        const tabButtons = await page.locator('button:has-text("Go"), button:has-text("TypeScript"), button:has-text("Python"), button:has-text("Markdown")').all();
        const tabNames = ['Go', 'TypeScript', 'Python', 'Markdown'];
        for (const name of tabNames) {
          try {
            const btn = page.getByRole('tab', { name, exact: true }).first();
            if (await btn.count() === 0) {
              // Fallback: some Mintlify versions render tabs as plain buttons, not role=tab
              const altBtn = page.locator(`button:text-is("${name}")`).first();
              if (await altBtn.count() > 0) {
                await altBtn.click({ timeout: 5000 });
              } else {
                result.tabs[name] = { error: 'tab button not found' };
                continue;
              }
            } else {
              await btn.click({ timeout: 5000 });
            }
            await page.waitForTimeout(150);
            result.tabs[name] = await measureActiveTab(page);
          } catch (e) {
            result.tabs[name] = { error: String(e && e.message || e) };
          }
        }
      } catch (e) {
        result.error = String(e && e.message || e);
      }
      out.write(JSON.stringify(result) + '\n');
      done++;
      process.stderr.write(`[${done}/${total}] ${path}\n`);
    }
    await page.close();
  }

  const workers = [];
  for (let i = 0; i < concurrency; i++) workers.push(worker());
  await Promise.all(workers);

  await browser.close();
  out.end();
  process.stderr.write(`DONE total=${total}\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
