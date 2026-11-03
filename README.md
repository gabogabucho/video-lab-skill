# Video lab

Creado por Gabriel Urrutia — @gabogabucho en X (https://x.com/gabogabucho).

Skill para que un agente (Cursor, Claude Code, Codex u otro que lea [Agent Skills](https://agentskills.io)) arme videos para redes de forma repetible: el mismo guion y los mismos archivos dan el mismo video. Motion graphics, crudo editado, o una mezcla de los dos.

La especificación que el agente tiene que seguir está en `SKILL.md`. Este README es para instalar el skill y dejar la máquina lista.

## Qué vas a tener

- `scripts/setup.sh` instala todo lo que pide la guía: ffmpeg, un venv de Python, Chromium (Playwright), la fuente Noto Sans ExtraBold y el modelo de caras YuNet. Lo podés correr de nuevo: si algo ya está, no lo reinstala de cero.
- `scripts/smoke.sh` renderiza un video corto de prueba. Si anda, queda `out/smoke/smoke.mp4`.
- `templates/proyecto/` es el esqueleto de un video. Los textos y los colores de ahí son de una marca inventada (Norte). No los publiques como si fueran de un cliente.
- No hay claves ni tokens en el repo. Lo único opcional está en `.env.example`, vacío.

## Preparar la máquina

Necesitás Linux con `sudo`, `apt` y conexión la primera vez. Desde la raíz del repo:

```bash
bash scripts/setup.sh
bash scripts/smoke.sh
```

El setup termina solo cuando la verificación pasa. El humo termina cuando existe el MP4 (2 segundos, 540×960, con el texto «¿Listo, ñandú?»). No uses ese archivo como pieza final: está a mitad de resolución y a 12 fps para que la prueba sea corta. Un video de verdad va a 1080×1920 (u otro formato de la guía) y a 30 fps.

La primera transcripción baja el modelo `small` de faster-whisper (cientos de MB, sin token). Si lo querés dejar listo antes:

```bash
bash scripts/setup.sh --prefetch-whisper
```

Para trabajar en un proyecto, activá el venv del skill:

```bash
source .venv/bin/activate
cp -a templates/proyecto ../mi-video
cd ../mi-video
```

## Instalar el skill

`SKILL.md` está en la raíz, así que **esta carpeta es el skill**. El nombre tiene que quedar `video-lab` (es el `name` del frontmatter). Con un symlink no tenés que volver a copiar cuando se actualiza.

Reemplazá `/ruta/al/repo` por la ruta real, la que te da `pwd` acá adentro.

### Cursor

Para vos, en cualquier proyecto:

```bash
mkdir -p ~/.cursor/skills
ln -sfn /ruta/al/repo ~/.cursor/skills/video-lab
```

Solo para un proyecto:

```bash
mkdir -p .cursor/skills
ln -sfn /ruta/al/repo .cursor/skills/video-lab
```

Reabrí el chat del agente para que lo vea. A partir de ahí le podés pedir un video para Reels, un motion graphic o que deje el entorno listo: tiene que leer el skill y seguir `SKILL.md`.

### Claude Code

```bash
mkdir -p ~/.claude/skills
ln -sfn /ruta/al/repo ~/.claude/skills/video-lab
```

O, dentro del proyecto donde vas a laburar:

```bash
mkdir -p .claude/skills
ln -sfn /ruta/al/repo .claude/skills/video-lab
```

### Codex

```bash
mkdir -p ~/.codex/skills
ln -sfn /ruta/al/repo ~/.codex/skills/video-lab
```

En un repo, Codex también mira `.agents/skills`:

```bash
mkdir -p .agents/skills
ln -sfn /ruta/al/repo .agents/skills/video-lab
```

### Otro agente

Si el agente entiende Agent Skills, la convención es una carpeta con `SKILL.md` adentro. Poné el symlink en el directorio de skills que use ese agente, con el nombre `video-lab`. Si solo acepta copiar, copiá el repo entero: sin la raíz con `SKILL.md`, no lo va a cargar.

El setup es de la máquina, no del agente. Aunque el skill esté instalado en los tres, `bash scripts/setup.sh` se corre una vez en esa Linux.

## Variables de entorno

No hace falta ninguna para renderizar. Si querés cambiar un default, copiá `.env.example` a un `.env` **fuera del repo** o exportá la variable en la shell. No commitees `.env`.

| Variable | Default | Para qué |
|---|---|---|
| `WHISPER_MODEL` | `small` | Modelo local. La guía usa `small` |
| `WHISPER_DEVICE` | `cpu` | |
| `WHISPER_COMPUTE` | `int8` | |
| `HF_TOKEN` | vacío | Dejalo vacío. Los modelos públicos no lo piden |
| `HF_HOME` | `~/.cache/huggingface` | Dónde se guardan los pesos |
| `VIDEO_LAB_YUNET` | `share/models/face_detection_yunet.onnx` | Si movés el modelo de caras |
| `VIDEO_LAB_FONT` | `share/fonts/texto.ttf` | La fuente con la que el setup verifica ñ y tildes |
| `VIDEO_LAB_X264_PRESET` | `slow` | Preset del MP4 final. El humo usa `veryfast` |

## Cómo se usa, en corto

1. Instalá el skill en el agente, como arriba.
2. Corré el setup y el humo en la máquina.
3. Copiá `templates/proyecto` a una carpeta nueva.
4. Reemplazá la marca inventada por la real (`brand/tokens.json`, las fuentes, el logo) y escribí el guion. Eso lo tiene que cerrar una persona: el agente no inventa colores, precios ni tomas.
5. Pedile al agente que siga el flujo A, B o C de `SKILL.md`.

El humo no transcribe ni detecta una cara de verdad. El setup sí comprueba que YuNet cargue, que la fuente tenga `¿¡áéíóúñ` y que la cadena HDR de ffmpeg arranque. El primer análisis de un crudo es el que baja Whisper.

## Si algo falla

- **`ensurepip` / `python3-venv`:** el setup instala `python3-venv` y el paquete de tu versión (`python3.12-venv` en Ubuntu 24.04). Volvé a correrlo.
- **Chromium:** `bash scripts/setup.sh` otra vez. `playwright install-deps` necesita sudo.
- **Hash de la fuente o de YuNet:** el archivo que llegó no es el que fijamos. No lo uses. Revisá la red y corré el setup de nuevo; si el upstream cambió el archivo, hay que actualizar el sha en `scripts/setup.sh` a propósito.
- **La transcripción tarda o baja mucho:** es el modelo `small` en CPU. Es lo que pide la guía. No lo cambies por una API.
- **El video de humo no aparece:** corré `bash scripts/smoke.sh` y leé la última línea. El MP4 tiene que quedar en `out/smoke/smoke.mp4`.

## Qué no entra

Música con licencia, voz generada por un servicio, y la declaración de contenido de IA en la plataforma. La guía los deja afuera a propósito. Tampoco hay claves: si algún día conectás un servicio externo, la clave va en el entorno, nunca en este repo.
