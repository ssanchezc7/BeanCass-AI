// Capturas de pantalla del recorrido completo (escritorio y móvil) con Playwright.
// Uso: node scripts/capturas.mjs <url-base> <carpeta-salida>
// Requiere Playwright instalado (no es dependencia del proyecto): npm i -g playwright && npx playwright install chromium
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

const base = process.argv[2] ?? 'http://localhost:3000'
const salida = process.argv[3] ?? 'capturas'
mkdirSync(salida, { recursive: true })

const vistas = [
  { nombre: 'escritorio', viewport: { width: 1280, height: 900 } },
  { nombre: 'movil', viewport: { width: 390, height: 844 } },
]

async function esperarResultado(page) {
  await page.getByRole('heading', { level: 1 }).first().waitFor()
  await page.waitForSelector('.result-page', { timeout: 60000 })
  await page.waitForTimeout(400)
}

const browser = await chromium.launch()
for (const vista of vistas) {
  const page = await browser.newPage({ viewport: vista.viewport })
  const foto = async (n) => page.screenshot({ path: join(salida, `${vista.nombre}-${n}.png`), fullPage: true })
  for (const cultivo of ['Fréjol', 'Yuca']) {
    const c = cultivo === 'Fréjol' ? 'frejol' : 'yuca'
    await page.goto(base, { waitUntil: 'networkidle' })
    if (cultivo === 'Fréjol') await foto('01-inicio')
    await page.getByRole('button', { name: `Comenzar con ${cultivo}` }).click()
    await page.waitForSelector('.dropzone')
    await foto(`02-carga-${c}`)
    await page.getByRole('button', { name: /Usar imagen de ejemplo/ }).click()
    await page.waitForSelector('.preview-image')
    await page.waitForTimeout(300)
    await foto(`03-ejemplo-${c}`)
    await page.getByRole('button', { name: /Analizar imagen/ }).click()
    await esperarResultado(page)
    await foto(`04-resultado-${c}`)
    const reporte = page.getByRole('button', { name: /Ver reporte|Ver informe/ })
    if (await reporte.count()) {
      await reporte.first().click()
      await page.waitForSelector('.report-sheet')
      await page.waitForTimeout(300)
      await foto(`05-reporte-${c}`)
    }
  }
  await page.close()
}
await browser.close()
console.log(`Capturas guardadas en ${salida}`)
