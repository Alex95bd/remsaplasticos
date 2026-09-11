"""Genera las ilustraciones SVG del sitio (logo, iconos y productos)."""

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "static" / "img"
OUT.mkdir(parents=True, exist_ok=True)

GRAD = """
  <defs>
    <linearGradient id="body" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <linearGradient id="cap" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{cap1}"/><stop offset="100%" stop-color="{cap2}"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff" stop-opacity=".75"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
  </defs>
"""


def svg(body: str, c1="#cfe9fb", c2="#8fd0ee", cap1="#1f7ad6", cap2="#0b4f9c", w=160, h=220) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img">{GRAD.format(c1=c1, c2=c2, cap1=cap1, cap2=cap2)}{body}</svg>\n'
    )


BOTTLE = svg(
    """
  <path d="M66 18h28v14c0 6 10 10 10 24v128c0 10-6 16-16 16H72c-10 0-16-6-16-16V56c0-14 10-18 10-24z"
        fill="url(#body)" stroke="#5aa9d6" stroke-width="2"/>
  <rect x="62" y="10" width="36" height="16" rx="4" fill="url(#cap)"/>
  <rect x="62" y="28" width="36" height="5" rx="2" fill="#9ec9e4"/>
  <path d="M70 70h20v90H70z" fill="url(#shine)" opacity=".8"/>
  <rect x="56" y="96" width="48" height="34" rx="6" fill="#ffffff" opacity=".55"/>
  <path d="M58 150h44M58 162h44" stroke="#7dbcdf" stroke-width="3" stroke-linecap="round" opacity=".6"/>
"""
)

JAR = svg(
    """
  <rect x="34" y="30" width="92" height="20" rx="6" fill="url(#cap)"/>
  <path d="M44 50h72c6 0 10 5 10 12v122c0 10-6 16-16 16H50c-10 0-16-6-16-16V62c0-7 4-12 10-12z"
        fill="url(#body)" stroke="#5aa9d6" stroke-width="2"/>
  <rect x="46" y="74" width="20" height="106" fill="url(#shine)" opacity=".7"/>
  <rect x="40" y="96" width="80" height="46" rx="8" fill="#ffffff" opacity=".5"/>
"""
)

JUG = svg(
    """
  <rect x="58" y="8" width="34" height="16" rx="4" fill="url(#cap)"/>
  <path d="M60 24h30v16c18 6 30 16 30 34v112c0 10-7 18-18 18H44c-11 0-18-8-18-18V74c0-18 12-28 34-34z"
        fill="url(#body)" stroke="#5aa9d6" stroke-width="2"/>
  <path d="M120 78h14c10 0 16 8 16 18v22c0 10-6 18-16 18h-14v-16h10c3 0 4-2 4-5v-16c0-3-1-5-4-5h-10z"
        fill="url(#body)" stroke="#5aa9d6" stroke-width="2"/>
  <rect x="36" y="92" width="16" height="86" fill="url(#shine)" opacity=".7"/>
  <rect x="32" y="112" width="80" height="44" rx="8" fill="#ffffff" opacity=".5"/>
"""
)

CARBOY = svg(
    """
  <rect x="62" y="6" width="36" height="16" rx="4" fill="url(#cap)"/>
  <path d="M64 22h32v12c22 8 34 22 34 44v106c0 14-9 24-24 24H54c-15 0-24-10-24-24V78c0-22 12-36 34-44z"
        fill="url(#body)" stroke="#5aa9d6" stroke-width="2"/>
  <path d="M40 96h80M40 118h80M40 140h80" stroke="#83c1e2" stroke-width="4" stroke-linecap="round" opacity=".55"/>
  <rect x="44" y="100" width="72" height="40" rx="10" fill="#ffffff" opacity=".45"/>
  <path d="M128 60h12c9 0 14 7 14 16v20c0 9-5 16-14 16h-12" fill="none" stroke="#5aa9d6"
        stroke-width="10" stroke-linecap="round"/>
"""
)

CAP = svg(
    """
  <ellipse cx="80" cy="86" rx="58" ry="26" fill="url(#cap)"/>
  <path d="M22 86v44c0 14 26 26 58 26s58-12 58-26V86z" fill="url(#cap)" opacity=".85"/>
  <ellipse cx="80" cy="86" rx="46" ry="19" fill="#ffffff" opacity=".22"/>
  <path d="M32 104v26M48 96v40M64 92v46M80 90v48M96 92v46M112 96v40M128 104v26"
        stroke="#ffffff" stroke-width="3" opacity=".35" stroke-linecap="round"/>
""",
    h=200,
)

PREFORM = svg(
    """
  <rect x="60" y="16" width="40" height="26" rx="4" fill="url(#cap)"/>
  <rect x="54" y="42" width="52" height="10" rx="3" fill="#9ec9e4"/>
  <path d="M64 52h32v104c0 18-6 30-16 30s-16-12-16-30z" fill="url(#body)" stroke="#5aa9d6" stroke-width="2"/>
  <rect x="70" y="62" width="10" height="92" fill="url(#shine)" opacity=".8"/>
  <path d="M62 22h36M62 30h36" stroke="#ffffff" stroke-width="3" opacity=".4"/>
"""
)

LOGO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0b63c5"/><stop offset="100%" stop-color="#16b8e0"/>
  </linearGradient></defs>
  <rect width="48" height="48" rx="13" fill="url(#g)"/>
  <path d="M20 9h8v5c0 3 4 4 4 9v14c0 4-2 6-6 6h-4c-4 0-6-2-6-6V23c0-5 4-6 4-9z" fill="#fff" opacity=".95"/>
  <rect x="19" y="6" width="10" height="5" rx="1.6" fill="#e8f6ff"/>
  <path d="M18 26h12v6H18z" fill="#0b63c5" opacity=".25"/>
</svg>
"""

LOGO_LIGHT = LOGO.replace('fill="url(#g)"', 'fill="rgba(255,255,255,.12)" stroke="rgba(255,255,255,.35)"')

FAVICON = LOGO

BOT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#ffffff"/><stop offset="100%" stop-color="#cfeafc"/>
  </linearGradient></defs>
  <circle cx="32" cy="32" r="30" fill="url(#b)"/>
  <rect x="16" y="22" width="32" height="24" rx="9" fill="#0b63c5"/>
  <circle cx="26" cy="33" r="4" fill="#fff"/><circle cx="38" cy="33" r="4" fill="#fff"/>
  <circle cx="26" cy="34" r="1.8" fill="#0b3f74"/><circle cx="38" cy="34" r="1.8" fill="#0b3f74"/>
  <path d="M32 14v8" stroke="#0b63c5" stroke-width="3" stroke-linecap="round"/>
  <circle cx="32" cy="12" r="3.5" fill="#16b8e0"/>
  <path d="M27 41h10" stroke="#8fd0ee" stroke-width="2.5" stroke-linecap="round"/>
</svg>
"""

FILES = {
    "cat-botellas-pet.svg": BOTTLE,
    "cat-frascos-pet.svg": JAR,
    "cat-garrafas-pead.svg": JUG,
    "cat-garrafas-pet.svg": svg(JUG.split("</defs>")[1].replace("</svg>\n", ""), c1="#e6f6ff", c2="#a9e0f5"),
    "cat-garrafones-y-botellones.svg": CARBOY,
    "cat-tapas.svg": CAP,
    "cat-preformas.svg": PREFORM,
    "logo.svg": LOGO,
    "logo-light.svg": LOGO_LIGHT,
    "favicon.svg": FAVICON,
    "bot-avatar.svg": BOT,
}

for name, content in FILES.items():
    (OUT / name).write_text(content, encoding="utf-8")
print(f"{len(FILES)} archivos SVG generados en {OUT}")
