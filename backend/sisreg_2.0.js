const puppeteer = require('puppeteer'); // v23.0.0 or later

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    const timeout = 5000;
    page.setDefaultTimeout(timeout);

    {
        const targetPage = page;
        await targetPage.setViewport({
            width: 1351,
            height: 317
        })
    }
    {
        const targetPage = page;
        await targetPage.goto('https://sisregiii.saude.gov.br/');
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('#usuario'),
            targetPage.locator('::-p-xpath(//*[@id=\\"usuario\\"])'),
            targetPage.locator(':scope >>> #usuario')
        ])
            .setTimeout(timeout)
            .fill('20325223FRANCK');
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(Senha :)'),
            targetPage.locator('#senha'),
            targetPage.locator('::-p-xpath(//*[@id=\\"senha\\"])'),
            targetPage.locator(':scope >>> #senha')
        ])
            .setTimeout(timeout)
            .fill('515462');
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('#usuario'),
            targetPage.locator('::-p-xpath(//*[@id=\\"usuario\\"])'),
            targetPage.locator(':scope >>> #usuario'),
            targetPage.locator('::-p-text(20325223FRANCK)')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 159.609375,
                y: 20.75,
              },
            });
    }
    {
        const targetPage = page;
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        await targetPage.keyboard.down('a');
    }
    {
        const targetPage = page;
        await targetPage.keyboard.up('a');
    }
    {
        const targetPage = page;
        await targetPage.keyboard.up('Control');
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('#usuario'),
            targetPage.locator('::-p-xpath(//*[@id=\\"usuario\\"])'),
            targetPage.locator(':scope >>> #usuario'),
            targetPage.locator('::-p-text(20325223FRANCK)')
        ])
            .setTimeout(timeout)
            .fill('20325223franck');
    }
    {
        const targetPage = page;
        await targetPage.keyboard.down('Tab');
    }
    {
        const targetPage = page;
        await targetPage.keyboard.up('Tab');
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(Senha :)'),
            targetPage.locator('#senha'),
            targetPage.locator('::-p-xpath(//*[@id=\\"senha\\"])'),
            targetPage.locator(':scope >>> #senha'),
            targetPage.locator('::-p-text(515462)')
        ])
            .setTimeout(timeout)
            .fill('515462');
    }
    {
        const targetPage = page;
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(targetPage.waitForNavigation());
        }
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(entrar)'),
            targetPage.locator('div.form-no-lbl > input'),
            targetPage.locator('::-p-xpath(//*[@id=\\"conteudoFull\\"]/div[1]/div[1]/div[8]/input)'),
            targetPage.locator(':scope >>> div.form-no-lbl > input'),
            targetPage.locator('::-p-text(entrar)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 21.6875,
                y: 9.625,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(AIH GERADA)'),
            targetPage.locator('li.sfHover > ul > li:nth-of-type(2) > a'),
            targetPage.locator('::-p-xpath(//*[@id=\\"barraMenu\\"]/ul/li[6]/ul/li[2]/a)'),
            targetPage.locator(':scope >>> li.sfHover > ul > li:nth-of-type(2) > a'),
            targetPage.locator('::-p-text(AIH Gerada)')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 71.875,
                y: 4.234375,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(Selecione a Prioridade) >>>> ::-p-aria([role=\\"combobox\\"])'),
            frame.locator('tr:nth-of-type(10) select'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center/table/tbody/tr[10]/td[2]/select)'),
            frame.locator(':scope >>> tr:nth-of-type(10) select')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 116.671875,
                y: 15,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(Eletiva) >>>> ::-p-aria([role=\\"combobox\\"])'),
            frame.locator('tr:nth-of-type(10) select'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center/table/tbody/tr[10]/td[2]/select)'),
            frame.locator(':scope >>> tr:nth-of-type(10) select')
        ])
            .setTimeout(timeout)
            .fill('E');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(PESQUISAR)'),
            frame.locator('tr:nth-of-type(12) input:nth-of-type(1)'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center/table/tbody/tr[12]/td/input[1])'),
            frame.locator(':scope >>> tr:nth-of-type(12) input:nth-of-type(1)'),
            frame.locator('::-p-text(PESQUISAR)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 20.515625,
                y: 8,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('tr:nth-of-type(3) > td:nth-of-type(3)'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center[2]/table/tbody/tr[3]/td[3])'),
            frame.locator(':scope >>> tr:nth-of-type(3) > td:nth-of-type(3)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 150.4375,
                y: 3,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('#fichaInternacao'),
            frame.locator('::-p-xpath(//*[@id=\\"fichaInternacao\\"])'),
            frame.locator(':scope >>> #fichaInternacao')
        ])
            .setTimeout(timeout)
            .click({
              count: 2,
              offset: {
                x: 88,
                y: 258,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('#fichaInternacao'),
            frame.locator('::-p-xpath(//*[@id=\\"fichaInternacao\\"])'),
            frame.locator(':scope >>> #fichaInternacao')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 88,
                y: 258,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('p');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/1/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.down('Control');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/1/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.down('c');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/1/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.up('c');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/1/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.up('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(VOLTAR)'),
            frame.locator('center > input:nth-of-type(1)'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center/input[1])'),
            frame.locator(':scope >>> center > input:nth-of-type(1)'),
            frame.locator('::-p-text(VOLTAR)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 48.171875,
                y: 7,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('tr:nth-of-type(4) > td:nth-of-type(3)'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center[2]/table/tbody/tr[4]/td[3])'),
            frame.locator(':scope >>> tr:nth-of-type(4) > td:nth-of-type(3)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 141.4375,
                y: 10,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('#fichaInternacao'),
            frame.locator('::-p-xpath(//*[@id=\\"fichaInternacao\\"])'),
            frame.locator(':scope >>> #fichaInternacao')
        ])
            .setTimeout(timeout)
            .click({
              count: 2,
              offset: {
                x: 83,
                y: 747,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('#fichaInternacao'),
            frame.locator('::-p-xpath(//*[@id=\\"fichaInternacao\\"])'),
            frame.locator(':scope >>> #fichaInternacao')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 83,
                y: 747,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('p');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/2/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.down('Control');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/2/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.down('c');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/2/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.up('c');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/2/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.up('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(VOLTAR)'),
            frame.locator('center > input:nth-of-type(1)'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center/input[1])'),
            frame.locator(':scope >>> center > input:nth-of-type(1)'),
            frame.locator('::-p-text(VOLTAR)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 81.171875,
                y: 5,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(Exibindo Página 1 de 1194 Proxima ) >>>> ::-p-aria([role=\\"textbox\\"])'),
            frame.locator('center:nth-of-type(3) input'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center[3]/table/tbody/tr/td/input)'),
            frame.locator(':scope >>> center:nth-of-type(3) input')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 31.9375,
                y: 13,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('body > center'),
            frame.locator('::-p-xpath(/html/body/center)'),
            frame.locator(':scope >>> body > center')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 436,
                y: 693,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(Proxima[role=\\"image\\"])'),
            frame.locator('center:nth-of-type(3) img'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center[3]/table/tbody/tr/td/a/img)'),
            frame.locator(':scope >>> center:nth-of-type(3) img')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 4.578125,
                y: 3,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('tr:nth-of-type(3) > td:nth-of-type(3)'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center[2]/table/tbody/tr[3]/td[3])'),
            frame.locator(':scope >>> tr:nth-of-type(3) > td:nth-of-type(3)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 110.71875,
                y: 22,
              },
            });
        await Promise.all(promises);
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('#fichaInternacao'),
            frame.locator('::-p-xpath(//*[@id=\\"fichaInternacao\\"])'),
            frame.locator(':scope >>> #fichaInternacao')
        ])
            .setTimeout(timeout)
            .click({
              count: 2,
              offset: {
                x: 49,
                y: 77,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await puppeteer.Locator.race([
            frame.locator('#fichaInternacao'),
            frame.locator('::-p-xpath(//*[@id=\\"fichaInternacao\\"])'),
            frame.locator(':scope >>> #fichaInternacao')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 49,
                y: 77,
              },
            });
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        await targetPage.keyboard.down('p');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/3/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.down('Control');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/3/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.down('c');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/3/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.up('c');
    }
    {
        const target = await browser.waitForTarget(t => t.url() === 'chrome-untrusted://print/3/0/print.pdf', { timeout });
        const targetPage = await target.page();
        targetPage.setDefaultTimeout(timeout);
        await targetPage.keyboard.up('Control');
    }
    {
        const targetPage = page;
        let frame = targetPage.mainFrame();
        frame = frame.childFrames()[0];
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(frame.waitForNavigation());
        }
        await puppeteer.Locator.race([
            frame.locator('::-p-aria(VOLTAR)'),
            frame.locator('center > input:nth-of-type(1)'),
            frame.locator('::-p-xpath(//*[@id=\\"main_page\\"]/form/center/input[1])'),
            frame.locator(':scope >>> center > input:nth-of-type(1)'),
            frame.locator('::-p-text(VOLTAR)')
        ])
            .setTimeout(timeout)
            .on('action', () => startWaitingForEvents())
            .click({
              offset: {
                x: 63.171875,
                y: 3,
              },
            });
        await Promise.all(promises);
    }

    await browser.close();

})().catch(err => {
    console.error(err);
    process.exit(1);
});
