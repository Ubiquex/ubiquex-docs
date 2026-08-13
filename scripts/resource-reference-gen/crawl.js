// UBI-150: site-wide overflow crawler -- reconstructed from UBI-148's own
// original crawl.js (STATE.md's own account: Playwright, waitUntil:'load'
// not 'networkidle' since the dev server's HMR websocket never lets
// networkidle resolve, page-level document.scrollWidth vs clientWidth,
// every `main pre` block's own scrollWidth vs clientWidth, flagged as a
// real bug only when no ancestor within 6 levels actually scrolls it).
// UBI-148's own copy lived in a prior session's own scratchpad
// (/private/tmp/.../scratchpad/ubi148/crawl.js), gone once that session
// ended -- recreated here from the real, detailed STATE.md account of its
// own methodology, now committed as real, tracked tooling (UBI-148's own
// original recommendation), not left in scratch a second time.
//
// Extends the original with crawl_overflow.js's own tab-clicking (built
// for UBI-144, since resource-reference pages carry Go/TypeScript/Python/
// Markdown tabs the original crawl.js never needed): if a page has real
// tab buttons, click through each and measure; otherwise (every other
// page type -- tutorial/concepts/cli-reference/index/install) measure
// once, exactly as UBI-148's own original did.
//
// Usage: node crawl.js <pages-file> <base-url> <out-jsonl> <concurrency> [viewport-width]
// viewport-width defaults to 1440 (UBI-148's own original baseline) --
// pass a real, different width (e.g. 1920) to measure a different real
// viewport population; never silently changed, always an explicit arg.

const { chromium } = require('playwright');
const fs = require('fs');

async function main() {
  const [pagesFile, baseUrl, outFile, concurrencyArg, viewportWidthArg] = process.argv.slice(2);
  const concurrency = parseInt(concurrencyArg || '4', 10);
  const viewportWidth = parseInt(viewportWidthArg || '1440', 10);
  const pages = fs.readFileSync(pagesFile, 'utf8').split('\n').map(l => l.trim()).filter(Boolean);

  const out = fs.createWriteStream(outFile, { flags: 'a' });
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: viewportWidth, height: 900 } });

  let idx = 0, done = 0;
  const total = pages.length;

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

  const tabNames = ['Go', 'TypeScript', 'Python', 'Markdown'];

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

        let hasTabs = false;
        for (const name of tabNames) {
          const btn = page.getByRole('tab', { name, exact: true }).first();
          if (await btn.count() > 0) { hasTabs = true; break; }
        }

        if (!hasTabs) {
          // UBI-148's own original shape: no tabs on this page type, one
          // real measurement of the page as loaded.
          result.tabs['default'] = await measureActiveTab(page);
        } else {
          for (const name of tabNames) {
            try {
              const btn = page.getByRole('tab', { name, exact: true }).first();
              if (await btn.count() === 0) {
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
