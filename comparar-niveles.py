#!/usr/bin/env python3
"""
comparar_niveles.py - Control rapido de un nivel corto (Breve o Intermedio) contra su Profundo.

No reemplaza tu lectura: te dice DONDE mirar primero.

Uso (desde la carpeta de tus HTML):
    python comparar_niveles.py --profundo Dios-Padre-Profundo.html --nivel Dios-Padre-Breve.html --tipo breve
    python comparar_niveles.py --profundo p1.html p2.html p3.html --nivel Inter.html --tipo intermedio

Solo usa la biblioteca estandar de Python (no hay que instalar nada).
"""
import argparse
import html
import math
import re
import sys
import unicodedata
from html.parser import HTMLParser

# ---------------------------------------------------------------- configuracion
CLASES_PERMITIDAS = {"hero-escatologico", "cuerpo-analisis", "original", "etq",
                     "tr", "tabla-scroll", "theology-table", "ref-personaje"}
ETIQUETAS_PROHIBIDAS = {"script", "style", "pre", "aside", "html", "head", "body", "footer"}
VOID = {"br", "img", "hr", "meta", "link", "input", "area", "base", "col",
        "embed", "source", "track", "wbr"}
RANGOS = {"breve": (700, 1000), "intermedio": (2000, 2500)}   # palabras de texto visible
PPM = 200                                                      # palabras por minuto

LIBROS = [
    "Genesis", "Exodo", "Levitico", "Numeros", "Deuteronomio", "Josue", "Jueces", "Rut",
    "1 Samuel", "2 Samuel", "1 Reyes", "2 Reyes", "1 Cronicas", "2 Cronicas", "Esdras",
    "Nehemias", "Ester", "Job", "Salmos", "Salmo", "Proverbios", "Eclesiastes", "Cantares",
    "Isaias", "Jeremias", "Lamentaciones", "Ezequiel", "Daniel", "Oseas", "Joel", "Amos",
    "Abdias", "Jonas", "Miqueas", "Nahum", "Habacuc", "Sofonias", "Hageo", "Zacarias",
    "Malaquias", "Mateo", "Marcos", "Lucas", "Juan", "Hechos", "Romanos", "1 Corintios",
    "2 Corintios", "Galatas", "Efesios", "Filipenses", "Colosenses", "1 Tesalonicenses",
    "2 Tesalonicenses", "1 Timoteo", "2 Timoteo", "Tito", "Filemon", "Hebreos", "Santiago",
    "1 Pedro", "2 Pedro", "1 Juan", "2 Juan", "3 Juan", "Judas", "Apocalipsis",
]


def norm(s):
    """Minusculas y sin tildes (para comparar)."""
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


_libros_re = "|".join(sorted((re.escape(l.lower()) for l in LIBROS), key=len, reverse=True))
REF_RE = re.compile(
    r"(?<![\w])(" + _libros_re + r")\s+(\d{1,3})"
    r"(?:\s?[-\u2013]\s?(\d{1,3}))?"
    r"(?::\s?(\d+(?:\s?[-\u2013]\s?\d+)?(?:\s?[,;]\s?\d+(?:\s?[-\u2013]\s?\d+)?)*))?"
)


# ---------------------------------------------------------------- parser HTML
class Analizador(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errores = [], []
        self.clases, self.etiquetas = set(), set()
        self.enlaces, self.estilos = [], 0
        self.h1, self.h2, self.headings = [], [], []
        self.pj = set()
        self.hero = False
        self.texto_cuerpo, self.texto_total = [], []
        self._cuerpo = 0
        self._ignorar = 0
        self._cur = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.etiquetas.add(tag)
        for c in (a.get("class") or "").split():
            self.clases.add(c)
        if tag == "a":
            self.enlaces.append(a.get("href", ""))
        if "style" in a:
            self.estilos += 1
        if tag == "span" and a.get("data-pj"):
            self.pj.add(a["data-pj"])
        classes = (a.get("class") or "").split()
        if tag == "header" and "hero-escatologico" in classes:
            self.hero = True
        if tag in ("script", "style"):
            self._ignorar += 1
        if tag == "div":
            if self._cuerpo:
                self._cuerpo += 1
            elif "cuerpo-analisis" in classes:
                self._cuerpo = 1
        if tag in ("h1", "h2"):
            self._cur = (tag, [])
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag in ("script", "style") and self._ignorar:
            self._ignorar -= 1
        if tag == "div" and self._cuerpo:
            self._cuerpo -= 1
        if tag in ("h1", "h2") and self._cur and self._cur[0] == tag:
            txt = " ".join("".join(self._cur[1]).split())
            (self.h1 if tag == "h1" else self.h2).append(txt)
            self.headings.append((tag, txt))
            self._cur = None
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errores.append(f"<{self.stack.pop()}> sin cerrar antes de </{tag}>")
            self.stack.pop()
        else:
            self.errores.append(f"cierre huerfano </{tag}>")

    def handle_data(self, data):
        if self._ignorar:
            return
        self.texto_total.append(data)
        if self._cuerpo:
            self.texto_cuerpo.append(data)
        if self._cur:
            self._cur[1].append(data)

    def cerrar(self):
        for t in self.stack:
            self.errores.append(f"<{t}> nunca se cerro")


def analizar(ruta):
    with open(ruta, encoding="utf-8") as f:
        src = f.read()
    p = Analizador()
    p.feed(src)
    p.close()
    p.cerrar()
    cuerpo = " ".join("".join(p.texto_cuerpo).split())
    total = " ".join("".join(p.texto_total).split())
    p.texto = cuerpo if cuerpo else total
    p.sin_cuerpo = not cuerpo
    return p


# ---------------------------------------------------------------- referencias
def parsear_versos(s):
    versos = set()
    for parte in re.split(r"[,;]", s):
        parte = parte.strip()
        m = re.match(r"(\d+)\s*[-\u2013]\s*(\d+)$", parte)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 <= b - a <= 200:
                versos.update(range(a, b + 1))
        elif parte.isdigit():
            versos.add(int(parte))
    return versos


def extraer_refs(texto):
    """Devuelve lista de (libro, capitulo, versos|None, texto_original) y el texto sin referencias."""
    t = norm(texto)
    refs = []
    for m in REF_RE.finditer(t):
        libro, cap = m.group(1), int(m.group(2))
        cap_fin, versos = m.group(3), m.group(4)
        etiqueta = m.group(0)
        if versos:
            refs.append((libro, cap, parsear_versos(versos), etiqueta))
        elif cap_fin:
            for c in range(cap, min(int(cap_fin), cap + 150) + 1):
                refs.append((libro, c, None, etiqueta))
        else:
            refs.append((libro, cap, None, etiqueta))
    sin_refs = REF_RE.sub(" ", t)
    return refs, sin_refs


def cobertura(refs):
    completos, versos = set(), {}
    for libro, cap, vs, _ in refs:
        if vs is None:
            completos.add((libro, cap))
        else:
            versos.setdefault((libro, cap), set()).update(vs)
    return completos, versos


# ---------------------------------------------------------------- reporte
class Reporte:
    def __init__(self):
        self.avisos = 0

    def ok(self, msg):
        print(f"  [OK]       {msg}")

    def revisar(self, msg):
        self.avisos += 1
        print(f"  [REVISAR]  {msg}")

    def info(self, msg):
        print(f"  [info]     {msg}")


def etiqueta_tiempo(palabras):
    minutos = max(1, math.ceil(palabras / PPM))
    if minutos < 60:
        return f"{minutos} min"
    h, m = divmod(minutos, 60)
    return f"{h} h" if m == 0 else f"{h} h {m} min"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Compara un nivel corto contra su Profundo.")
    ap.add_argument("--profundo", nargs="+", required=True, help="HTML del Profundo (una o varias partes)")
    ap.add_argument("--nivel", required=True, help="HTML del Breve o Intermedio")
    ap.add_argument("--tipo", required=True, choices=["breve", "intermedio"])
    args = ap.parse_args()

    # ----- cargar
    partes = [analizar(r) for r in args.profundo]
    prof_texto = " ".join(p.texto for p in partes)
    prof_pj = set().union(*(p.pj for p in partes))
    nivel = analizar(args.nivel)
    r = Reporte()

    print("\n=== COMPARADOR PROFUNDO vs NIVEL CORTO ===")
    print(f"Profundo: {', '.join(args.profundo)}")
    print(f"Nivel:    {args.nivel}  (tipo: {args.tipo})\n")

    # ----- 1. tamano
    print("1. Tamano")
    pal_prof = len(prof_texto.split())
    pal_niv = len(nivel.texto.split())
    lo, hi = RANGOS[args.tipo]
    r.info(f"Profundo: {pal_prof} palabras ({etiqueta_tiempo(pal_prof)})")
    r.info(f"Nivel:    {pal_niv} palabras ({etiqueta_tiempo(pal_niv)}), {pal_niv / max(pal_prof, 1):.1%} del Profundo")
    if nivel.sin_cuerpo:
        r.revisar("no encontre <div class=\"cuerpo-analisis\">; conte todo el texto de la pagina")
    if lo <= pal_niv <= hi:
        r.ok(f"dentro del rango {lo}-{hi} palabras")
    else:
        r.revisar(f"fuera del rango {lo}-{hi} palabras")

    # ----- 2. referencias biblicas
    print("\n2. Referencias biblicas (solo nombres completos de libros, p. ej. 'Juan 3:16')")
    refs_p, _ = extraer_refs(prof_texto)
    refs_n, sin_refs_n = extraer_refs(nivel.texto)
    completos, versos = cobertura(refs_p)
    nuevas = []
    for libro, cap, vs, et in refs_n:
        key = (libro, cap)
        if key in completos:
            continue
        if vs is None:
            if key not in versos:
                nuevas.append(et)
        else:
            if not vs <= versos.get(key, set()):
                nuevas.append(et)
    nuevas = sorted(set(nuevas))
    r.info(f"{len(refs_n)} referencias en el nivel, {len(refs_p)} en el Profundo")
    if nuevas:
        for et in nuevas:
            r.revisar(f"'{et}' no aparece (o no completa) en el Profundo")
    else:
        r.ok("todas las referencias del nivel estan en el Profundo")

    # ----- 3. cifras y fechas
    print("\n3. Cifras y fechas (numeros de 3 o 4 cifras)")
    _, sin_refs_p = extraer_refs(prof_texto)
    pat_num = re.compile(r"(?<![\d.,])\d{3,4}(?![\d.,]\d)")
    num_p = set(pat_num.findall(sin_refs_p))
    num_n = set(pat_num.findall(sin_refs_n))
    extra = sorted(num_n - num_p)
    if extra:
        r.revisar("cifras que NO estan en el Profundo: " + ", ".join(extra))
    else:
        r.ok("no hay cifras nuevas")

    # ----- 4. hebreo / griego
    print("\n4. Palabras en griego o hebreo")
    pat_gh = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF\u0590-\u05FF]+")
    gh_p = {unicodedata.normalize("NFC", w) for w in pat_gh.findall(prof_texto)}
    gh_n = {unicodedata.normalize("NFC", w) for w in pat_gh.findall(nivel.texto)}
    extra = sorted(gh_n - gh_p)
    if extra:
        r.revisar("palabras que NO estan en el Profundo: " + ", ".join(extra))
    else:
        r.ok("no hay palabras originales nuevas")
    if args.tipo == "breve" and gh_n:
        r.revisar("el Breve no deberia llevar hebreo ni griego")

    # ----- 5. nombres propios
    print("\n5. Nombres propios (heuristica: puede dar falsos positivos)")
    vocab = {w.lower() for w in re.findall(r"[A-Za-z\u00C0-\u017F]+", prof_texto)}
    ignorar = {"para", "intermedio", "profundo", "breve", "nivel", "tabla", "veredicto",
               "aplicacion", "seguir", "leyendo"}
    ignorar |= {w for l in LIBROS for w in norm(l).split() if not w.isdigit()}
    nombres = {w for w in re.findall(r"\b[A-Z\u00C1\u00C9\u00CD\u00D3\u00DA\u00D1][a-z\u00E1\u00E9\u00ED\u00F3\u00FA\u00F1\u00FC]{3,}\b", nivel.texto)
               if w.lower() not in vocab and norm(w) not in ignorar}
    if nombres:
        r.revisar("palabras con mayuscula que no aparecen nunca en el Profundo: " + ", ".join(sorted(nombres)))
    else:
        r.ok("no hay nombres nuevos")
    nuevos_pj = sorted(nivel.pj - prof_pj)
    if nuevos_pj:
        r.revisar("slugs de personajes que no estan en el Profundo: " + ", ".join(nuevos_pj))
    else:
        r.ok("los slugs de personajes coinciden con el Profundo")

    # ----- 6. advertencias y etiquetas
    print("\n6. Advertencias y etiquetas")
    for nombre in ("NO VERIFICADO", "SIN BASE"):
        cp, cn = prof_texto.count(nombre), nivel.texto.count(nombre)
        r.info(f"{nombre}: Profundo {cp}, nivel {cn}")
    if prof_texto.count("NO VERIFICADO") and not nivel.texto.count("NO VERIFICADO"):
        r.revisar("el Profundo tiene NO VERIFICADO y el nivel no: comprueba que no se perdieron advertencias")
    for etq in ("[TEXTO]", "[HIST\u00d3RICO]", "[ACAD\u00c9MICO]", "[TRADICI\u00d3N]", "[ESPECULACI\u00d3N]"):
        r.info(f"{etq}: Profundo {prof_texto.count(etq)}, nivel {nivel.texto.count(etq)}")

    # ----- 7. HTML
    print("\n7. Reglas de HTML")
    fuera = sorted(nivel.clases - CLASES_PERMITIDAS)
    r.revisar("clases fuera de la lista: " + ", ".join(fuera)) if fuera else r.ok("solo clases permitidas")
    prohib = sorted(nivel.etiquetas & ETIQUETAS_PROHIBIDAS)
    r.revisar("etiquetas prohibidas: " + ", ".join(prohib)) if prohib else r.ok("sin etiquetas prohibidas")
    r.revisar(f"hay {len(nivel.enlaces)} enlace(s) <a>: " + ", ".join(nivel.enlaces[:5])) if nivel.enlaces else r.ok("sin enlaces")
    r.revisar(f"hay {nivel.estilos} atributo(s) style") if nivel.estilos else r.ok("sin atributos style")
    if nivel.errores:
        for e in nivel.errores[:8]:
            r.revisar("estructura: " + e)
    else:
        r.ok("todas las etiquetas estan bien cerradas")
    r.ok("tiene hero") if nivel.hero else r.revisar("falta <header class=\"hero-escatologico\">")

    # ----- 8. estructura del contenido
    print("\n8. Estructura del contenido")
    r.ok("tiene 'Veredicto'") if any("veredicto" in norm(h) for h in nivel.h2) else r.revisar("no encuentro el <h2>Veredicto</h2>")
    r.ok("tiene seccion de aplicacion") if any("aplicacion" in norm(h) for h in nivel.h1) else r.revisar("no encuentro un <h1> de aplicacion")
    r.ok("tiene 'Tabla de verificacion'") if any("tabla de verificacion" in norm(h) for h in nivel.h2) else r.revisar("no encuentro el <h2>Tabla de verificacion</h2>")
    ultimo = nivel.headings[-1][1] if nivel.headings else ""
    if "seguir leyendo" in norm(ultimo):
        r.ok("termina con la puerta 'Para seguir leyendo'")
    else:
        r.revisar("el ultimo titulo no es 'Para seguir leyendo' (puerta al siguiente nivel)")

    # ----- 9. tiempos escritos en el texto
    print("\n9. Tiempos escritos en el texto (los calcula la plantilla)")
    pat_t = re.compile(r"(?i)\b\d+\s*(?:min\b|minutos?|horas?|palabras)|tiempo de lectura|minutos de lectura")
    hallados = pat_t.findall(nivel.texto)
    r.revisar("el texto menciona tiempos o cantidades: " + ", ".join(sorted(set(hallados)))) if hallados else r.ok("no escribe tiempos")

    # ----- resumen
    print("\n" + "=" * 52)
    if r.avisos:
        print(f"RESULTADO: {r.avisos} punto(s) para revisar. Empieza por los [REVISAR].")
    else:
        print("RESULTADO: sin avisos automaticos. Igual falta tu lectura.")
    print("=" * 52 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())