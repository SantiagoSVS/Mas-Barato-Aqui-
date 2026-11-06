# Despliegue gratuito: Render y Neon

La aplicación queda en una sola dirección de internet, para que el tutor no dependa del equipo
de Santiago para abrirla.

| Pieza | Dónde | Limitación del plan gratis |
|---|---|---|
| API e interfaz (una imagen Docker) | [Render](https://render.com/docs/free) | Se duerme tras 15 minutos sin tráfico y tarda cerca de 1 minuto en despertar |
| Base de datos | [Neon](https://neon.com/pricing) | 1 GB; se suspende tras 5 minutos sin uso y despierta en segundos |
| Captura de precios | Tarea programada del equipo de Santiago | El equipo debe estar encendido para que haya precios nuevos |

Solo el worker toca las tiendas, y corre fuera de Render porque el plan gratis no lo permite como
proceso permanente. Si el equipo está apagado, la aplicación sigue funcionando con la última
captura, y cada precio muestra su fecha.

## Lo que hace Santiago (crear cuentas y poner claves)

### 1. Base de datos en Neon

1. Crea una cuenta en [neon.com](https://neon.com) (no pide tarjeta).
2. Crea un proyecto con **Postgres 17**, región **AWS US East (N. Virginia)**.
3. Copia la cadena de conexión (empieza por `postgresql://`). Es una clave: no la pegues en
   documentos ni en el repositorio.

### 2. Copiar los datos a Neon

Copia el esquema y todo el historial. En PowerShell, desde la raíz del proyecto, con Docker
encendido y tu cadena en lugar de `TU_CADENA_DE_NEON`:

```powershell
docker exec mas-barato-db pg_dump -U mas_barato -d mas_barato_aqui --no-owner --no-privileges -Fc -f /tmp/datos.dump
docker exec mas-barato-db pg_restore --no-owner --no-privileges -d "TU_CADENA_DE_NEON" /tmp/datos.dump
```

### 3. Servicio en Render

1. Crea una cuenta en [render.com](https://render.com) y conéctala con GitHub.
2. Elige **New → Blueprint** y selecciona el repositorio. Render lee `render.yaml`.
3. Cuando lo pida, pon `DATABASE_URL` (la cadena de Neon) y `ANTHROPIC_API_KEY`.
4. Espera a que termine la primera construcción. La dirección queda como
   `https://mas-barato-aqui.onrender.com` o parecida.

### 4. Que la captura guarde en Neon

En tu `.env` local, reemplaza el valor de `DATABASE_URL` por la cadena de Neon y agrega
`DB_TIMEOUT_CONEXION_S=20`. Guarda la línea anterior comentada por si quieres volver. Las pruebas
no se afectan: usan `TEST_DATABASE_URL`, que sigue en Docker.

Actualiza la tarea programada, que ahora admite capturas más largas:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\programar_captura.ps1
```

## Cómo comprobar que quedó bien

1. Abre `https://<tu-dirección>/api/salud`: debe mostrar las tres tiendas y su última captura.
2. Abre la dirección principal y busca «audífonos Xiaomi que no pasen de 150 mil».
3. Abre el historial y recarga la página: debe seguir en la misma pantalla.

## Si el equipo de captura se queda apagado

Una oferta sin captura en 3 días sale de la comparación, para no recomendar un precio viejo. Si el
equipo pasa más de 3 días apagado, la aplicación se queda sin ofertas y avisa que no tiene precios
recientes; el historial se conserva. Basta encenderlo: la captura corre sola y los precios vuelven
cuando termina, unos 40 minutos después. El plazo se cambia con `OFERTA_VIGENCIA_DIAS` en el panel
de Render.

## El día de la revisión

- Abre la aplicación un par de minutos antes y haz una búsqueda: así ya está despierta.
- Revisa `/api/salud` para saber la fecha de la última captura. Si tiene más de 3 días, enciende el
  equipo con tiempo: sin capturas recientes la aplicación no muestra precios.
- Ten capturas de pantalla por si falla internet.

## Protección de los créditos

El sitio es público, así que tiene dos límites:

- 20 consultas por minuto por dirección IP.
- 300 llamadas al modelo en 24 horas, en total (`LIMITE_CONSULTAS_MODELO_POR_DIA`, valor inicial
  que se cambia en el panel de Render). Al llegar al tope, la aplicación pide intentar mañana.

Además, la cuenta de Anthropic tiene el límite de gasto de US$5 sin recarga automática. Las
claves viven solo en los paneles de Render y en el `.env` local.

## Probar la imagen en local

```powershell
docker build -t mas-barato-aqui .
docker run --rm -p 10000:10000 -e DATABASE_URL="postgresql://mas_barato:TU_CLAVE@host.docker.internal:5432/mas_barato_aqui" mas-barato-aqui
```

Queda en <http://localhost:10000>, con el proveedor falso, sin gastar créditos.
