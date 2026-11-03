"""Resumen de comandos. El procedimiento completo está en SKILL.md."""


def main() -> int:
    print(
        """video-lab — sistema determinístico de videos para redes

Preparar la máquina (una vez):
  bash scripts/setup.sh
  bash scripts/smoke.sh

Dentro de un proyecto copiado de templates/proyecto, con el venv activo:
  python scripts/marca.py verificar
  python scripts/normalizar.py --proyecto .
  python scripts/analizar.py --proyecto .
  python scripts/editar.py proponer --fuente A
  python scripts/editar.py construir
  python scripts/sync.py analisis/anclas.json
  python scripts/entregar.py
  python scripts/qa.py

Leé SKILL.md antes de producir un video. El guion y la marca los aprueba una persona.
"""
    )
    return 0
