// Contenido informativo de cultivos, clases y modelos (datos del estudio comparativo UNEMI).
// Las descripciones son generales y no incluyen dosis ni productos: siempre se remite a un técnico agrícola.
import type { Crop } from './tipos'

export interface ClassContent {
  code: string
  name: string
  description: string
  symptoms: string
  advice: string
}

export interface CropContent {
  name: string
  english: string
  model: string
  image: string
  classesSummary: string
  dataset: string
  classes: ClassContent[]
  metricsTest: {
    images: number
    accuracy: number
    f1Macro: number
    errors: number
    diseasedAsHealthy: number
    note: string
  }
  parameters: string
  limitations: string[]
}

const CONSULTA = 'Confirma el resultado con un técnico agrícola o una entidad de sanidad vegetal antes de tomar decisiones de manejo.'

export const CROPS_CONTENT: Record<Crop, CropContent> = {
  bean: {
    name: 'Fréjol',
    english: 'Beans',
    model: 'MobileNetV2',
    image: '/bean-leaf.png',
    classesSummary: 'Mancha angular · Roya · Hoja sana',
    dataset: 'Beans — Makerere AI Lab (fotografías de campo en Uganda)',
    parameters: '2,26 M',
    classes: [
      {
        code: 'angular_leaf_spot',
        name: 'Mancha angular',
        description: 'Enfermedad fúngica (Pseudocercospora griseola) frecuente en climas cálidos y húmedos.',
        symptoms: 'Manchas pardas o grisáceas de bordes angulares, delimitadas por las nervaduras; pueden unirse y causar caída de hojas.',
        advice: CONSULTA,
      },
      {
        code: 'bean_rust',
        name: 'Roya',
        description: 'Enfermedad fúngica (Uromyces appendiculatus) que se dispersa por esporas transportadas por el viento.',
        symptoms: 'Pústulas pequeñas, redondas y de color óxido, a menudo rodeadas de un halo amarillo; polvo rojizo al frotarlas.',
        advice: CONSULTA,
      },
      {
        code: 'healthy',
        name: 'Hoja sana',
        description: 'El modelo no detectó los patrones de mancha angular ni de roya en la fotografía.',
        symptoms: 'Lámina de color verde uniforme, sin manchas, pústulas ni decoloraciones visibles.',
        advice: 'Sigue observando el cultivo: el modelo solo distingue entre estas dos enfermedades y no evalúa otras plagas o deficiencias.',
      },
    ],
    metricsTest: {
      images: 128,
      accuracy: 0.9688,
      f1Macro: 0.969,
      errors: 4,
      diseasedAsHealthy: 0,
      note: 'Los 4 errores ocurrieron entre enfermedades; ninguna hoja enferma se clasificó como sana.',
    },
    limitations: [
      'Validado con 128 imágenes de Test del dataset Beans; el desempeño puede bajar con fotos de otras condiciones.',
      'Solo reconoce mancha angular y roya: otras enfermedades pueden asignarse a una de estas clases.',
    ],
  },
  cassava: {
    name: 'Yuca',
    english: 'Cassava',
    model: 'EfficientNetB0',
    image: '/cassava-leaf.png',
    classesSummary: 'CBB · CBSD · CGM · CMD · Hoja sana',
    dataset: 'iCassava 2019 (fotografías de campo en Uganda)',
    parameters: '4,06 M',
    classes: [
      {
        code: 'cbb',
        name: 'CBB — tizón bacteriano',
        description: 'Enfermedad bacteriana (Xanthomonas axonopodis pv. manihotis).',
        symptoms: 'Manchas angulares de aspecto acuoso, amarillamiento y marchitez de hojas; puede haber exudados en tallos.',
        advice: CONSULTA,
      },
      {
        code: 'cbsd',
        name: 'CBSD — estría marrón',
        description: 'Enfermedad viral (virus de la estría marrón de la yuca) transmitida por mosca blanca y material de siembra.',
        symptoms: 'Clorosis amarillenta a lo largo de las nervaduras secundarias y manchas amarillas difusas; afecta también a las raíces.',
        advice: CONSULTA,
      },
      {
        code: 'cgm',
        name: 'CGM — daño por ácaro verde',
        description: 'Daño causado por el ácaro verde de la yuca (Mononychellus tanajoa).',
        symptoms: 'Moteado o punteado clorótico, hojas pequeñas y deformadas, sobre todo en los brotes jóvenes.',
        advice: CONSULTA,
      },
      {
        code: 'cmd',
        name: 'CMD — mosaico',
        description: 'Enfermedad viral (begomovirus del mosaico de la yuca) transmitida por mosca blanca y estacas infectadas.',
        symptoms: 'Mosaico de zonas amarillas y verdes, hojas retorcidas o deformadas y reducción del tamaño de la planta.',
        advice: CONSULTA,
      },
      {
        code: 'healthy',
        name: 'Hoja sana',
        description: 'El modelo no detectó patrones de las cuatro enfermedades evaluadas.',
        symptoms: 'Hoja de color verde uniforme, sin moteados, mosaicos ni manchas visibles.',
        advice: 'Este resultado no garantiza que la planta esté sana: en Test, el modelo clasificó 40 hojas enfermas como sanas. Revisa otras hojas y consulta a un técnico ante cualquier duda.',
      },
    ],
    metricsTest: {
      images: 1885,
      accuracy: 0.8228,
      f1Macro: 0.7544,
      errors: 334,
      diseasedAsHealthy: 40,
      note: 'CBB (recall ≈ 0,61) y CBSD se confunden entre sí; 40 hojas enfermas se clasificaron como sanas.',
    },
    limitations: [
      'Es el modelo más débil del estudio: exactitud ≈ 82 % y recall de CBB ≈ 0,61.',
      'Una predicción de «Hoja sana» nunca debe tomarse como garantía de ausencia de enfermedad.',
      'El dataset contiene 12 y 11 imágenes duplicadas entre Train y Validation/Test (documentadas en el estudio).',
    ],
  },
}

export const GENERAL_LIMITATIONS = [
  'Resultados válidos bajo las condiciones de los datasets usados (iCassava 2019 y Makerere AI Lab Beans); no garantizan el mismo desempeño con cualquier fotografía.',
  'No se repitieron los entrenamientos con distintas semillas, por lo que no se estimó la variabilidad de las métricas.',
  'Un clasificador siempre elige una de sus clases, incluso si la foto no es una hoja: por eso se muestran avisos de calidad.',
  'Es una herramienta educativa y orientativa; no constituye un diagnóstico agronómico.',
]

export const SCORE_COLORS = ['green', 'gold', 'sage', 'mint', 'slate'] as const

export function classContent(crop: Crop, code: string): ClassContent | undefined {
  return CROPS_CONTENT[crop].classes.find((c) => c.code === code)
}

export function percent(value: number): number {
  return Math.round(value * 100)
}

export function percentLabel(value: number): string {
  if (value > 0 && value < 0.005) return '<1'
  return String(percent(value))
}
