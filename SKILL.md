---
name: video-lab
description: >
  Sistema determinístico para armar videos de redes (TikTok, Reels, Shorts,
  feed, YouTube): motion graphics, edición de video crudo o mixto, cuadro a
  cuadro, desde un guion.json y un kit de marca. Usalo para instalar el
  entorno desde cero, normalizar crudo, transcribir, reencuadrar caras,
  animar con render(t), sintetizar efectos, componer con ffmpeg y pasar el
  control de calidad. Use it when asked to make a social video, motion
  graphics, a deterministic edit, burned-in subtitles, or to set up this
  video lab. No lo uses para un timeline manual, para inventar la marca, ni
  para elegir música con licencia.
---

# Video lab

Creado por Gabriel Urrutia — @gabogabucho en X (https://x.com/gabogabucho).

El video final es una función del tiempo. Para cada instante `t` hay una sola imagen y un solo sonido. Nada depende del reloj real, del azar sin semilla, de la velocidad de la máquina ni de una decisión tomada en el momento del render.

Lo que pide criterio (qué tramos usar, si una toma sirve, qué promete el texto, si la marca se pronuncia bien) se resuelve **antes** y queda en archivos. El render solo lee esos archivos.

```
brand/ + guion.json + crudo/ + voz
        │
        ▼
analisis/*.json          (una vez: palabras, silencios, escenas, caras)
        │
        ▼
capa de video            cortes, encuadre, color
capa gráfica             HTML + render(t), con alfa si va encima del crudo
capa de audio            voz, efectos sintetizados
        │
        ▼
ffmpeg  →  MP4 + hoja de contactos
```

## Cuándo usar este skill

- Hay que dejar la máquina lista desde cero y después producir un video.
- El pedido es un video para TikTok, Reels, Shorts, historias, feed o YouTube: motion graphics, persona a cámara, demo, testimonio, o una mezcla.
- Hay que rehacer un video ya definido y que salga igual si se vuelve a renderizar.

## Cuándo no usarlo

- El corte de verdad vive en un editor de timeline. Este sistema no importa proyectos de Premiere o Resolve.
- Hay que elegir música, conseguir la licencia, o declarar contenido generado con IA en la plataforma. Eso lo decide quien publica.
- Hay que inventar una marca, un precio, una función o un testimonio para "completar" el video.

## Reglas que no se negocian

1. **Un solo reloj.** Todo se calcula desde `t` en segundos de la línea de tiempo final. En la capa gráfica están prohibidos las transiciones y animaciones CSS, `setTimeout`, `setInterval`, `requestAnimationFrame` y `Date.now()`.
2. **Azar con semilla.** Cualquier variación sale de un generador con semilla fija. En la capa gráfica la semilla vuelve a 7 al empezar cada `render(t)`.
3. **Sin estado.** `render(t)` no depende del cuadro anterior. Cada cuadro se arma de cero.
4. **Análisis congelado.** Transcripción, caras, silencios y escenas se calculan una vez y se guardan en `analisis/`. Si se vuelven a calcular, se versionan. El render nunca analiza. Volver a correr `analizar.py` borra la marca de revisión humana.
5. **Formato de trabajo estable.** Todo crudo se normaliza antes de usarse: 30 fps constantes, SDR BT.709 cuando el material es HDR, y un intermedio conocido (`trabajo/*.mov`, yuv420p, audio pcm 48 kHz).
6. **Fuentes locales.** Tienen que cubrir `¿¡áéíóúñÁÉÍÓÚÑü·`. El render espera `document.fonts.ready` y 400 ms antes del primer cuadro.
7. **Zona segura como dato.** El texto y lo importante viven adentro del rectángulo de la sección de formatos. La hoja de contactos lo dibuja en rojo.
8. **El guion manda.** Textos, tiempos, tramos, encuadres y eventos de sonido viven en `guion.json`. Las plantillas y los scripts solo leen.
9. **Verdad de producto.** Lo que se lee en pantalla (función, precio, promesa, dato) tiene que existir de verdad. La plantilla de este repo es una marca inventada: no se publica así.

## Preparar la máquina

Una vez por máquina, desde la raíz de este skill:

```bash
bash scripts/setup.sh
bash scripts/smoke.sh
```

`setup.sh` es idempotente: se puede correr de nuevo. Instala ffmpeg, el venv (numpy, Pillow, fonttools, opencv, faster-whisper, Playwright), Chromium, Noto Sans ExtraBold y el modelo YuNet. Al final corre `python -m video_lab.verificar`.

`smoke.sh` tiene que dejar `out/smoke/smoke.mp4`. Es un video de 2 s, 540×960, 12 fps, con marca inventada. Sirve para ver que el tubo anda. No es un entregable.

El modelo de transcripción (`WHISPER_MODEL`, default `small`) se baja la primera vez que se analiza un crudo, no durante el setup. Para bajarlo antes: `bash scripts/setup.sh --prefetch-whisper`. No hace falta token.

Activá el venv del skill antes de trabajar en un proyecto:

```bash
source /ruta/al/skill/.venv/bin/activate
```

## Estructura de un proyecto

Copiá la plantilla y trabajá ahí. No edites `templates/` para un cliente.

```bash
cp -a templates/proyecto ../mi-video
cd ../mi-video
```

```
proyecto/
├── brand/
│   ├── tokens.json
│   ├── fonts/                 texto.ttf y, si difieren, titulo.ttf y mono.ttf
│   └── logo.png               PNG con alfa
├── crudo/                     originales, si hay
├── guion.json                 fuente de verdad
├── analisis/                  palabras, silencios, escenas, caras, mapa, warp
├── datos/                     JSON que cita una escena
├── trabajo/                   intermedios. Lo crea el render
├── tramos/                    lo crea editar construir
├── capas/graficos.html        motor + plantillas. No se reescribe entre proyectos
├── scripts/                   wrappers a este paquete
└── out/                       entregas
```

La guía no lista `trabajo/` en el árbol del principio y después lo usa. Acá es la carpeta del intermedio. `entregar.py` no está en la guía: junta el render gráfico, los efectos, la mezcla y las entregas para no dejar el orden suelto.

## Formatos y zonas seguras

| Formato | Resolución | Uso | Zona (x0–x1, y0–y1) |
|---|---|---|---|
| 9:16 | 1080×1920 | TikTok, Reels, Shorts, historias | 80–940, 150–1480 |
| 4:5 | 1080×1350 | Feed de Instagram y Facebook | 60–1020, 60–1290 |
| 1:1 | 1080×1080 | Feed, LinkedIn | 60–1020, 60–1020 |
| 16:9 | 1920×1080 | YouTube, web | 96–1824, 54–1026 |

En 9:16 la franja de abajo y la de la derecha se dejan libres: ahí van los botones y la descripción. Si el mismo video sale en varios formatos, diseñalo para el más estrecho o generá una versión por formato desde el mismo guion.

Un video a otra escala pero con el mismo aspecto (el humo es 540×960) usa la zona proporcional. Otro aspecto se rechaza.

Los tamaños de `texto_en_pantalla` están pensados para un ancho de 1080. El render los escala por `ancho / 1080`.

## El guion

Un solo JSON. Los tiempos de `escenas` y de `eventos_sfx` están en la **línea de tiempo final**. `duracion: "auto"` es la suma de los tramos de `edicion`. En un video solo gráfico, `duracion` es un número.

`"fin"` y `"fin-3.5"` se resuelven cuando ya se conoce la duración. `zoom.t` es distinto: son segundos desde que empieza ese tramo, no desde el inicio del video. Un evento `"t": "zoom"` cae en el primer zoom.

`audio.voz`:

- `null` — silencio (motion graphics todavía sin voz, o la prueba de humo).
- `"fuente"` — el audio del crudo ya editado. `limpieza: true` aplica el filtro de la sección de limpieza.
- `"voz.mp3"` — un archivo relativo al proyecto. Si no viene del crudo, primero va el mapa de la sección de voz externa.

`audio.musica` no entra en la mezcla. Si no es null, el script avisa y la ignora.

La plantilla y `examples/guion-crudo.json` muestran los dos contratos. Los textos de la plantilla ("12 min", "Pedido 184", `norte.ejemplo`) son inventados. Reemplazalos por datos verificados antes de renderizar para publicar.

Claves de color opcionales, si hace falta dejar las tomas parejas:

```json
"color": {"eq": "contrast=1.05:saturation=1.08:gamma=0.98"}
```

o `"color": {"lut": "brand/look.cube"}`. Sin esa clave no se pinta un look.

## Kit de marca

Sale de una fuente real (sitio, manual, archivos del cliente). No se inventa para cerrar el video.

Para mirar un sitio sin escribir `tokens.json`:

```bash
python scripts/marca.py desde-css https://ejemplo.com/
python scripts/marca.py desde-css https://ejemplo.com/estilos.css
```

Imprime los `href` de CSS, las variables `--algo: #hex` y las `url()` de fuentes. La misma búsqueda que los `curl | grep` de la guía. Una persona confirma los valores y recién ahí se edita `brand/tokens.json`.

```bash
python scripts/marca.py verificar
python scripts/marca.py logo --entrada logo-original.png --salida brand/logo.png
```

`verificar` exige los colores de la guía, `font.texto`, los tres estilos de texto, `radio`, y que cada fuente de `brand/fonts/` tenga los caracteres. El logo, si está, tiene que ser PNG con alfa. Si las cuatro esquinas son blancas, `logo` las vuelve transparentes y recorta.

`setup.sh` deja Noto Sans ExtraBold en `share/fonts/texto.ttf` y lo copia a la plantilla. Es un comodín de cobertura latina, no la voz de una marca. Cuando llega la fuente real, se reemplaza el archivo y se corre `marca.py verificar`.

## Flujos

En los tres, pará y mostrá el guion antes de renderizar para publicar. La lista de abajo es el orden de trabajo, no un permiso para decidir el concepto.

### A. Solo gráfico

1. Conseguir el kit real y correr `python scripts/marca.py verificar`.
2. Escribir `guion.json`. Hook de 2 a 3 s, escenas de 2 a 2,5 s, cierre de 3 a 4 s. Una idea por escena. `duracion` numérica. `edicion` vacía.
3. Reusar las plantillas de `capas/graficos.html`. No reescribas el motor.
4. `python scripts/entregar.py` renderiza sin alfa, sintetiza los efectos, mezcla y corre el control de calidad. Para una pasada intermedia, `--sin-qa` no saltea el hecho de mirar cuadros: sacá una hoja igual con `python scripts/qa.py`.
5. Guion de voz con tiempos por escena. Grabación o generación, afuera de este repo.
6. Transcribir esa voz (`analizar.py` sobre un wav/mov), elegir anclas, `python scripts/sync.py analisis/anclas.json`, volver a `entregar.py`. El render usa `analisis/warp.json`.
7. Entregas y revisión humana.

### B. Crudo editado

1. Poner los archivos en `crudo/` y declararlos en `fuentes` (`"A": "crudo/toma.mp4"`).
2. `python scripts/normalizar.py`. De acá en adelante se usa `trabajo/`, no el crudo.
3. `python scripts/analizar.py`. Revisión humana de la transcripción antes de cualquier subtítulo.
4. `python scripts/editar.py proponer --fuente A`. Es una propuesta de jump cuts. **No la copies al guion sin un ok de una persona.** La toma, si hay varias, no la elige este script.
5. La persona escribe `edicion` en el guion. Encuadre `cara` o `centro`. Zooms de golpe como en el ejemplo.
6. `python scripts/entregar.py` construye la capa de video si falta o si el guion es más nuevo, limpia la voz si `voz` es `"fuente"` y `limpieza` es true, renderiza la capa gráfica **con alfa**, mezcla y chequea.
7. Subtítulos solo después del archivo de revisión (más abajo).

### C. Mixto

La `edicion` alterna crudo y tramos gráficos. Un tramo gráfico es una placa del color de la marca:

```json
{"fuente": "color", "color": "#2f4b3c", "in": 0, "out": 2.5, "velocidad": 1.0}
```

`in`/`out` son la duración de la placa, igual que en un clip. La capa gráfica tiene que cubrir ese tramo por completo. `--fondo` en `entregar.py` es el caso de prueba: sin edición, placa de `color.fondo` y gráficos con alfa. Con edición, manda la edición y `--fondo` no reemplaza la capa de video.

## Capa gráfica

`capas/graficos.html` tiene el motor de la guía (`P`, `lerp`, `eo`, `ei`, `eio`, `eb`, `rnd`, `mkCap`, `showCap`) y las plantillas:

| Plantilla | Qué hace | Datos |
|---|---|---|
| `texto_bloque` | Hook, fondo detrás de cada palabra | `texto` |
| `titulo` | Palabra por palabra, sin pastilla | `texto` |
| `caos_a_orden` | Chips desde una posición con semilla hasta una grilla | `elementos` |
| `interfaz` / `interfaz_lateral` | Tarjeta de producto | `datos` (objeto o ruta a un JSON) |
| `antes_despues` | Dos estados, cortina | `antes`, `despues` |
| `lista_animada` | Ítems que entran de a uno | `texto`, `items` |
| `numero_grande` | Contador con formato `es-AR` | `valor`, `prefijo`, `sufijo`, `texto` |
| `cierre` | Logo, frase, CTA, URL tipeada | `texto`, `cta`, `url` |
| `subtitulos` | No es una escena: se dibujan solos si están activos | — |

Recetas que el motor ya puede calcular, usadas por esas plantillas: aparecer con rebote, subir y aparecer, tipeo, contador, cortina (`clip-path`), elementos que se ordenan desde `rnd()`.

Los subtítulos se ocultan mientras hay `texto_bloque`, `titulo`, `cierre` o `numero_grande`, para no tapar un título. Van en la zona media-baja **de la zona segura**, con borde, y la palabra activa usa el color de acento.

La guía agrupa de a 3 en el snippet y la regla dice bloques de 2 a 4 palabras sin cortar la frase. Se sigue la regla, y el `.srt` usa los mismos bloques que la imagen.

Para activar subtítulos hacen falta las tres cosas:

1. `subtitulos.activar: true` en el guion, después de la revisión.
2. `analisis/final.palabras.json`, que escribe `editar construir` al reubicar las palabras.
3. Un archivo `analisis/transcripcion.revisada` cuyo contenido es exactamente la palabra `revisada`. Lo escribe una persona. El agente no lo crea. `analizar.py` lo borra si corre de nuevo.

## Crudo, en detalle

**Normalizar.** HDR (`smpte2084`, `arib-std-b67`, `smpte428`) usa la cadena `zscale` + `tonemap=hable` de la guía. Si no es HDR, solo `fps=30,format=yuv420p`. Rotación: no se pasa `-noautorotate`; ffmpeg aplica el display matrix solo. Si el archivo no tiene audio, se agrega silencio pcm para que el intermedio se pueda concatenar. Si la salida ya está bien y es más nueva que el crudo, no se reencodea.

**Analizar.** Transcripción con faster-whisper (`small`, CPU, int8, salvo que el entorno diga otra cosa), el audio a 16 kHz mono, tiempos por palabra. Silencios `noise=-35dB:d=0.25`. Escenas `gt(scene,0.3)`. Caras con YuNet cada 3 cuadros, huecos interpolados y media móvil de 15, como la guía. Si no aparece ninguna cara, `cx` queda en el centro y se avisa.

**Proponer.** Salta silencios de 0,25 s o más y las muletillas `eh`, `este` y `o sea`. Deja 0,08 s de aire (adentro de 0,05–0,10). El encuadre de la propuesta es `centro`. No mira energía, gracia ni "la mejor toma".

**Construir.** Encuadre `centro` sin zoom: ffmpeg, con el recorte al aspecto de salida. Encuadre `cara`, o cualquier tramo con `zoom`: bucle de Python a ffmpeg por tubo, el centro x sale de `analisis/<toma>.cara.json`. El zoom sostiene `escala` durante `dur`.

La guía pone `-ss`/`-to` antes de `-i`, y eso corta en un keyframe. Acá van después de `-i`, con la misma cadena (`setpts`, crop, `atempo`, crf 14), para que el corte caiga en el tiempo del guion.

**Limpieza de voz**, cuando se pide:

```
highpass=f=80,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-1.5
```

El loudness de la pieza es el de la mezcla, no este.

## Voz externa

1. Transcribir la voz igual que el crudo.
2. Elegir anclas con una persona: qué momento del guion cae en qué palabra o silencio.
3. Guardar `analisis/anclas.json` con `R` (segundos del audio) y `A` (segundos de la animación) y correr `python scripts/sync.py analisis/anclas.json`.

Reglas para las anclas:

- Golpes fuertes: en el silencio de después de la frase, nunca en el medio.
- Cortes de escena: unas centésimas antes de la primera palabra de la frase nueva.
- Un sello, un botón, un dato: sobre la palabra que lo nombra.
- Al final: 0,8 a 1 s de cierre quieto después de la última palabra.
- Ningún tramo a más de 3× más rápido o más lento. Si pasa, `sync.py` se niega y hay que mover un ancla.

`render(t)` recibe el tiempo de animación: el cuadro `i` del archivo está en el segundo `i / fps` de la línea de tiempo final, y a la página se le pasa `warp(i / fps)`. Los eventos de sonido del guion ya están en esa línea de tiempo final, así que se escriben en ese segundo, sin pasarlos por `warp`. `warp_de` también devuelve la inversa (animación → tiempo real) por si un efecto se anotó en el reloj de la animación original; el guion no la aplica solo. Si la voz estira la pieza, los `t` del guion tienen que estar en el tiempo del audio.

## Efectos, mezcla, entregas

Efectos sintetizados, semilla 11, sin librerías de samples: `pop`, `click`, `whoosh`, `impacto`, `thump`, `ding`.

| Momento | Efecto |
|---|---|
| Aparecen en serie | `pop`, el tono puede variar |
| Golpe o cambio fuerte | `impacto`, en un silencio |
| Corte o barrido | `whoosh`, ~0,1 s antes |
| Tipeo | `click` |
| Botón, confirmación | `click` + `ding` suave |
| Sello, algo que cae | `thump` |
| Zoom de golpe | `pop` grave o `thump` corto. En el guion, `"t": "zoom"` |

Con alguien hablando, los efectos van más bajos que en un video solo gráfico: acompañan. La mezcla los deja en 0,42 y los baja cuando entra la voz (`sidechaincompress`). El objetivo de la mezcla es **-14 LUFS**, TP -1,5, LRA 11.

La música queda afuera. Para pauta hace falta licencia comercial. Se suma después, 15 a 20 dB bajo la voz, con un golpe alineado al primer momento fuerte.

Entregas, en `out/` (o al lado de `--salida`):

1. `final.mp4` — voz y efectos.
2. `final_sin_audio.mp4` — mismos tiempos, sin audio.
3. `efectos.wav`
4. `subtitulos.srt` si los subtítulos están activos y revisados.

`componer.sh` es el filtro de la guía. El preset de x264 de esa pasada es `slow`, salvo `VIDEO_LAB_X264_PRESET`. El humo lo pone en `veryfast` para no esperar el preset de entrega.

## Control de calidad

Automático, `python scripts/qa.py`:

- Hay video y audio, el tamaño es el del guion, la duración cierra y los cuadros son `fps × duración` (tolerancia de 2 cuadros; `nb_frames` del contenedor suele venir vacío, se cuentan de verdad).
- Loudness integrado. En piezas de 8 s o más, si `I` cae fuera de −18 a −10, el chequeo falla. En un clip de 2 s el número se imprime y no se usa como veredicto: la medición es inestable.
- `out/hoja.png`: cuadros con el rectángulo rojo. En 9:16 escalado a 270×480 el rectángulo es `x=20,y=37,w=215,h=333`, el de la guía. En un video largo el paso es un cuadro cada 60. En uno corto se reparte la hoja para que no salga un solo cuadro.

Humano, mirando la hoja y escuchando:

- [ ] Ningún texto toca el borde rojo.
- [ ] No hay cuadros negros ni vacíos en los cortes.
- [ ] Acentos, signos y números se leen, con formato local.
- [ ] El momento clave cae en su palabra.
- [ ] La marca se pronuncia bien.
- [ ] En crudo: el encuadre no tiembla, la cara no se corta, el corte no se come una sílaba.
- [ ] El subtítulo es la palabra que se está diciendo.

## Lo que no se decide solo

- El concepto y el guion, antes de animar o de editar.
- Qué toma usar, y si un momento es gracioso, emotivo o natural.
- El kit de marca.
- Funciones, precios y promesas en pantalla.
- La imagen de una persona real. Hace falta permiso, sobre todo en pauta.
- La pronunciación de la marca.
- La música con licencia y la declaración de contenido generado con IA.

Tampoco se crea `analisis/transcripcion.revisada`.

## Límites

- El sistema no mira el video como una persona. Trabaja con cuadros, transcripciones y métricas.
- No recorta una persona sobre un fondo cualquiera ni sigue un movimiento fino. Con pantalla verde se puede usar `chromakey` de ffmpeg; no está automatizado.
- 4K, HDR y clips largos conviene normalizarlos y recortarlos antes. El camino de la cara y el de la capa gráfica son cuadro por cuadro.
- La transcripción se equivoca con nombres, marcas y modismos.
- Dos máquinas con el mismo Chromium y las mismas fuentes se acercan mucho. No prometas bits idénticos entre versiones de Chromium: el render no usa azar ni reloj, y el antialiasing puede cambiar.

## Supuestos de esta implementación

- Linux con apt, ffmpeg (libx264, zscale, loudnorm, qtrle) y Python 3.10+.
- El modelo de caras es YuNet 2023mar de opencv_zoo, guardado como `face_detection_yunet.onnx`. La guía no da URL.
- La fuente de la plantilla es Noto Sans ExtraBold (OFL), porque la guía exige los caracteres y no adjunta un archivo.
- `zoom.t` es local al tramo. `"t": "zoom"` en un efecto apunta al primer zoom.
- Un tramo `fuente: "color"` es la placa del flujo mixto.
- `-ss`/`-to` van después de `-i`.
- Los bloques de subtítulos siguen la regla de 2 a 4 palabras, no el agrupado fijo de a 3 del snippet.
- `render(t)` recibe el float, no un texto cortado a 4 decimales, y la cantidad de cuadros se redondea (`round(fps * duración)`) para que `30 × 2,5` no pierda un cuadro por coma flotante.
- El `.srt` no tiene ejemplo en la guía; se escribe con los mismos bloques que la imagen.
- No hay proveedor de voz ni de música, y no hay claves. Generar la voz es un paso externo.

## Variables de entorno

Ver `.env.example`. Ninguna es una clave obligatoria.

| Variable | Default | Para qué |
|---|---|---|
| `WHISPER_MODEL` | `small` | Modelo local de faster-whisper |
| `WHISPER_DEVICE` | `cpu` | |
| `WHISPER_COMPUTE` | `int8` | |
| `HF_TOKEN` | vacío | Solo si el modelo no es público. No lo pongas en el repo |
| `HF_HOME` | caché de Hugging Face | Dónde quedan los pesos |
| `VIDEO_LAB_YUNET` | `share/models/face_detection_yunet.onnx` | |
| `VIDEO_LAB_FONT` | `share/fonts/texto.ttf` | La fuente que verifica el setup |
| `VIDEO_LAB_X264_PRESET` | `slow` | Solo el MP4 final |

## Comandos

```bash
python scripts/marca.py verificar
python scripts/marca.py desde-css https://ejemplo.com/estilos.css
python scripts/normalizar.py
python scripts/analizar.py
python scripts/editar.py proponer --fuente A
python scripts/editar.py construir
python scripts/sync.py analisis/anclas.json
python scripts/graficos.py --alfa
python scripts/sfx.py
python scripts/entregar.py
python scripts/qa.py
```

`entregar.py` ya llama a construir (si hay edición), gráficos, efectos, voz, `componer.sh` y `qa.py`. Los otros comandos están para correr un paso solo.
