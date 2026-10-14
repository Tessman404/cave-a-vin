const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 900, height: 1200 } });
  await p.goto('file://' + process.argv[2]); await p.screenshot({ path: process.argv[3], type: 'jpeg', quality: 88 }); await b.close(); })();
