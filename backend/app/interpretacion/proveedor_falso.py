"""Proveedor falso: interpreta con reglas simples, sin modelo de lenguaje ni clave de API.

Sirve para que el sistema funcione y se pueda probar mientras se elige el proveedor real
(sección 4, decisión pendiente). Responde un JSON con el mismo esquema que el modelo real y
pasa por la misma validación, así que el resto del sistema no nota la diferencia.

No reemplaza al modelo de lenguaje: entiende solo las palabras de sus listas. Su exactitud
también se puede medir con el script de evaluación, como línea base frente al modelo real.
No consume tokens.
"""

import json
import re
import unicodedata

from app.interpretacion.proveedor import ProveedorModelo, RespuestaModelo

# Tipo de producto: (nombre canónico, palabras que lo indican). Las frases largas van primero.
PRODUCTOS = [
    ("freidora de aire", ["freidora de aire", "air fryer", "airfryer", "freidora"]),
    ("portátil", ["computador portatil", "computadora portatil", "portatil", "laptop", "notebook"]),
    ("celular", ["celular", "telefono", "smartphone", "movil", "iphone"]),
    ("tablet", ["tablet", "tableta", "ipad"]),
    ("televisor", ["smart tv", "televisor", "television", "tv"]),
    ("audífonos", ["audifonos", "auriculares", "airpods"]),
    ("tenis", ["zapatillas", "tenis"]),
    ("nevera", ["nevera", "refrigerador"]),
    ("lavadora", ["lavadora"]),
    ("licuadora", ["licuadora"]),
    ("reloj inteligente", ["reloj inteligente", "smartwatch"]),
]

MARCAS = {
    "samsung": "Samsung", "apple": "Apple", "iphone": "Apple", "ipad": "Apple", "airpods": "Apple",
    "xiaomi": "Xiaomi", "redmi": "Xiaomi", "motorola": "Motorola", "huawei": "Huawei",
    "honor": "Honor", "oppo": "Oppo", "lenovo": "Lenovo", "hp": "HP", "asus": "Asus",
    "acer": "Acer", "dell": "Dell", "lg": "LG", "sony": "Sony", "jbl": "JBL", "oster": "Oster",
    "imusa": "Imusa", "kalley": "Kalley", "ninja": "Ninja", "holstein": "Holstein",
    "adidas": "Adidas", "nike": "Nike", "puma": "Puma", "reebok": "Reebok",
    "new balance": "New Balance",
}

# Modelos con número: "galaxy a55", "iphone 15 pro", "redmi note 13", "moto g84"
MODELOS = re.compile(
    r"\b(galaxy (?:tab )?[a-z]{0,2}\d{1,3}\w*(?: (?:ultra|plus|fe|pro))?"
    r"|iphone \d{1,2}(?: (?:pro max|pro|plus|mini))?"
    r"|redmi(?: note)? \d{1,2}\w*(?: pro)?"
    r"|moto [a-z]\d{1,3}\w*"
    r"|ideapad \w+)\b"
)

URGENCIA = ["rapido", "urgente", "pronto", "ya mismo", "para manana", "para hoy", "lo antes posible", "express"]

LIMITES = r"(?:menos de|maximo de|maximo|hasta|por debajo de|no mas de|que no pase de|no supere|tope de|presupuesto de|presupuesto)"
CANTIDAD = r"(\d+(?:[.,']\d+)*|un|medio)"
UNIDAD = r"(millones|millon|palos|palo|mil|lucas|luca|k)?"

COLORES = ["negro", "blanco", "gris", "azul", "rojo", "rosado", "verde", "plateado", "dorado", "morado"]
USOS = {"correr": "correr", "gimnasio": "gimnasio", "gym": "gimnasio", "la universidad": "universidad",
        "estudiar": "estudio", "gaming": "videojuegos", "jugar": "videojuegos", "trabajar": "trabajo",
        "la oficina": "trabajo"}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar sin importar cómo escribió el usuario."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def _contiene(texto: str, frase: str) -> bool:
    return re.search(rf"\b{re.escape(frase)}\b", texto) is not None


# Si no nombra el tipo de producto, la familia del modelo lo indica: "galaxy a55" es un celular
PRODUCTO_POR_MODELO = [
    (r"\bgalaxy tab\b", "tablet"),
    (r"\b(?:galaxy [a-z]{0,2}\d|redmi|moto [a-z]\d)", "celular"),
    (r"\bideapad\b", "portátil"),
]


def buscar_producto(texto: str) -> str | None:
    for canonico, palabras in PRODUCTOS:
        if any(_contiene(texto, p) for p in palabras):
            return canonico
    for patron, canonico in PRODUCTO_POR_MODELO:
        if re.search(patron, texto):
            return canonico
    return None


def buscar_marca(texto: str) -> str | None:
    for palabra, marca in sorted(MARCAS.items(), key=lambda m: -len(m[0])):
        if _contiene(texto, palabra):
            return marca
    return None


def buscar_modelo(texto: str) -> str | None:
    coincidencia = MODELOS.search(texto)
    if coincidencia is None:
        return None
    palabras = coincidencia.group(1).split()
    # "galaxy a55" -> "Galaxy A55"; "iphone 15 pro" -> "iPhone 15 Pro"
    return " ".join("iPhone" if p == "iphone" else p.upper() if any(c.isdigit() for c in p) else p.capitalize() for p in palabras)


def _a_pesos(cantidad: str, unidad: str | None) -> int | None:
    if cantidad == "un":
        numero = 1.0
    elif cantidad == "medio":
        numero = 0.5
    else:
        limpia = cantidad.replace("'", "").replace(".", "") if unidad in (None, "") else cantidad.replace(",", ".")
        try:
            numero = float(limpia.replace(",", ""))
        except ValueError:
            return None
    multiplicador = {"millon": 1_000_000, "millones": 1_000_000, "palo": 1_000_000, "palos": 1_000_000,
                     "mil": 1_000, "luca": 1_000, "lucas": 1_000, "k": 1_000}.get(unidad or "", 1)
    pesos = round(numero * multiplicador)
    return pesos if pesos >= 1_000 else None  # un número suelto pequeño no es un precio


def buscar_precio_maximo(texto: str) -> int | None:
    """Presupuesto máximo: "menos de 800 mil", "máximo 2 millones", "hasta $1.500.000", "2 palos"."""
    # Expresiones sin número: "millón y medio", "medio millón"
    texto = re.sub(r"\b(?:un )?millon y medio\b", "1,5 millones", texto)
    texto = re.sub(r"\bmedio millon\b", "500 mil", texto)
    texto = re.sub(r"\bun millon\b", "1 millon", texto)
    patron = rf"{LIMITES}\s*(?:unos |de )?\$?\s*{CANTIDAD}\s*{UNIDAD}(?:\s*y medio)?"
    coincidencia = re.search(patron, texto)
    if coincidencia is None:
        return None
    pesos = _a_pesos(coincidencia.group(1), coincidencia.group(2))
    if pesos is not None and coincidencia.group(0).endswith("y medio") and coincidencia.group(2):
        pesos += _a_pesos("medio", coincidencia.group(2)) or 0
    return pesos


def buscar_atributos(texto: str) -> dict[str, str]:
    atributos: dict[str, str] = {}
    if gama := re.search(r"\bgama (alta|media|baja)\b", texto):
        atributos["gama"] = gama.group(1)
    if ram := re.search(r"\b(\d{1,2})\s*gb de ram\b|\bram de (\d{1,2})\s*gb\b", texto):
        atributos["ram"] = f"{ram.group(1) or ram.group(2)} GB"
    for valor, unidad, siguiente in re.findall(r"\b(\d{2,4})\s*(gb|tb)\b(\s*de ram)?", texto):
        if not siguiente:
            atributos["almacenamiento"] = f"{valor} {unidad.upper()}"
    if litros := re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:litros|litro|lts|lt|l)\b", texto):
        atributos["capacidad"] = f"{litros.group(1).replace('.', ',')} L"
    if pulgadas := re.search(r"\b(\d{2,3}(?:[.,]\d)?)\s*(?:pulgadas|\")", texto):
        atributos["pantalla"] = f"{pulgadas.group(1)} pulgadas"
    if talla := re.search(r"\btalla (\d{2}(?:[.,]5)?|xs|s|m|l|xl|xxl)\b", texto):
        atributos["talla"] = talla.group(1).upper()
    for color in COLORES:
        # Acepta el plural: "negros", "azules", "grises"
        if re.search(rf"\b{color}(?:s|es)?\b", texto):
            atributos["color"] = color
            break
    for frase, uso in USOS.items():
        if _contiene(texto, f"para {frase}"):
            atributos["uso"] = uso
            break
    return atributos


class ProveedorFalso(ProveedorModelo):
    nombre = "falso"

    def completar(self, instrucciones: str, consulta: str) -> RespuestaModelo:
        texto = normalizar(consulta)
        producto = buscar_producto(texto)
        marca = buscar_marca(texto)
        criterios = {
            "producto": producto,
            "marca": marca,
            "modelo": buscar_modelo(texto),
            "atributos": buscar_atributos(texto),
            "precio_max_cop": buscar_precio_maximo(texto),
            "prioridad": "entrega_rapida" if any(_contiene(texto, u) for u in URGENCIA) else "costo_total",
            "confianza": 0.9 if producto else (0.4 if marca else 0.2),
            "requiere_aclaracion": producto is None,
        }
        return RespuestaModelo(texto=json.dumps(criterios, ensure_ascii=False), tokens_entrada=0, tokens_salida=0)
