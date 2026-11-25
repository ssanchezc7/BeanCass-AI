// Prueba E2E de aceptación con Playwright contra la app en ejecución (web + API).
// Uso: node scripts/e2e.mjs [url-base] [carpeta-con-archivos-invalidos]
//   La carpeta debe contener: texto.jpg, doc.pdf, anim.gif, corrupta.png, 20mb.jpg, 1x1.png
//   Con API_OFF=1 solo verifica el comportamiento con la API apagada.
// Requiere Playwright (no es dependencia del proyecto): npm i playwright && npx playwright install chromium
import { chromium } from 'playwright'
import { join } from 'node:path'

const base = process.argv[2] ?? 'http://localhost:3000'
const invalidos = process.argv[3]
const apiOff = process.env.API_OFF === '1'
let fallos = 0
const ok = (cond, msg) => { console.log(`${cond ? 'OK  ' : 'FALLA'} ${msg}`); if (!cond) fallos++ }

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
const erroresConsola = []
page.on('pageerror', (e) => erroresConsola.push(String(e)))

async function irACarga(cultivo) {
  await page.goto(base, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: `Comenzar con ${cultivo}` }).click()
  await page.waitForSelector('.dropzone')
}

async function resultadoDeEjemplo(cultivo) {
  await irACarga(cultivo)
  await page.getByRole('button', { name: /Usar imagen de ejemplo/ }).click()
  await page.waitForSelector('.preview-image')
  await page.getByRole('button', { name: /Analizar imagen/ }).click()
  await page.waitForSelector('.result-page', { timeout: 30000 })
  const titulo = await page.locator('.prediction-top h2').innerText()
  const barras = await page.locator('.score-row').evaluateAll((rows) => rows.map((r) => r.innerText.replace(/\s+/g, ' ')))
  return { titulo, barras }
}

if (apiOff) {
  await irACarga('Fréjol')
  await page.waitForSelector('.service-banner', { timeout: 10000 }).catch(() => null)
  ok(await page.locator('.service-banner').count() === 1, 'Con la API apagada se muestra el aviso de servicio sin conexión')
  await page.getByRole('button', { name: /Usar imagen de ejemplo/ }).click()
  await page.waitForSelector('.preview-image')
  await page.getByRole('button', { name: /Analizar imagen/ }).click()
  await page.waitForSelector('.api-error', { timeout: 35000 })
  const msg = await page.locator('.api-error').innerText()
  ok(/servidor|conexión/i.test(msg), `Error recuperable mostrado: "${msg.split('\n')[0]}"`)
  ok(await page.getByRole('button', { name: /^Reintentar$/ }).count() >= 1, 'Hay botón Reintentar')
  ok(await page.locator('h1').count() > 0, 'La página sigue renderizada (no pantalla en blanco)')
} else {
  const frejol = await resultadoDeEjemplo('Fréjol')
  console.log('   Fréjol →', frejol.titulo, '|', frejol.barras.join(' · '))
  const yuca = await resultadoDeEjemplo('Yuca')
  console.log('   Yuca   →', yuca.titulo, '|', yuca.barras.join(' · '))
  ok(frejol.barras.length === 3 && yuca.barras.length === 5, 'Barras reales: 3 clases (fréjol) y 5 (yuca)')
  ok(JSON.stringify(frejol.barras) !== JSON.stringify(yuca.barras), 'Las probabilidades cambian según la imagen')
  await page.getByRole('button', { name: /Ver reporte/ }).click()
  await page.waitForSelector('.report-sheet')
  ok((await page.locator('.report-title h1').innerText()).includes('yuca'), 'Reporte disponible también para yuca')
  ok(await page.locator('.report-probs tr').count() === 5, 'El reporte incluye las 5 probabilidades reales')

  const texto = await page.content()
  ok(!/simulad|Prototipo visual|No se analiza realmente/i.test(texto), 'No quedan textos de simulación')

  await page.goto(base, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /Sobre los modelos/ }).first().click()
  ok(await page.locator('dialog.about-dialog[open]').count() === 1, 'Se abre el diálogo «Sobre los modelos»')
  await page.keyboard.press('Escape')
  ok(await page.locator('dialog.about-dialog[open]').count() === 0, 'El diálogo se cierra con Escape')

  if (invalidos) {
    const casos = [
      ['texto.jpg', /no es una imagen JPEG o PNG/],
      ['doc.pdf', /PDF/],
      ['anim.gif', /GIF/],
      ['corrupta.png', /dañado|incompleto/],
      ['20mb.jpg', /máximo es 8 MB/],
      ['1x1.png', /1×1 px/],
    ]
    for (const [archivo, patron] of casos) {
      await irACarga('Fréjol')
      await page.locator('input[type=file]').setInputFiles(join(invalidos, archivo))
      await page.waitForSelector('.form-error', { timeout: 10000 })
      const msg = await page.locator('.form-error').innerText()
      ok(patron.test(msg) && (await page.getByRole('button', { name: /Analizar imagen/ }).isDisabled()),
        `Cliente rechaza ${archivo}: "${msg.trim()}"`)
    }
  }
}

ok(erroresConsola.length === 0, `Sin errores de JavaScript en la página${erroresConsola.length ? ': ' + erroresConsola.join(' | ') : ''}`)
await browser.close()
console.log(fallos ? `\n${fallos} comprobación(es) fallida(s)` : '\nTodas las comprobaciones pasaron')
process.exit(fallos ? 1 : 0)
