# xime-glow — Instrucciones para Claude

## Qué es
App de ventas de la tienda Xime Glow: productos con precio sugerido, clientas, ventas (incluidas a crédito
con abonos y saldo), catálogo, generación de posts para Instagram y mejora automática de fotos de producto.
Se usa sobre todo desde el **celular**.

## Arquitectura
- **Frontend:** `index.html` (~1,300 líneas, todo el JS vanilla dentro del HTML). Secciones: Vender, Clientas,
  Productos, Catálogo, Panel y Reglas (ajustes).
- **Datos en el navegador:** el estado completo vive en `localStorage` (`cargarEstado` / `guardarEstado`).
- **Servidor:** `app.py` (Flask en Render, `render.yaml`, 1 worker, timeout 120 s):
  - `/mejorar` (POST, campo `foto`): quita el fondo con `rembg`, pone fondo lila y devuelve JPG. Es pesado.
  - `/datos` (GET/POST): guarda y entrega el estado como **un solo documento JSON** para sincronizar PC y celular.
    Protegido con `SYNC_PIN` si está configurado; si no, queda abierto.
  - SQLite en `DATA_DIR` (`/var/data`). Si no hay disco persistente cae a `/tmp` y **se borra al reiniciar**.
- **Sincronización:** el front sube el estado 1.5 s después del último cambio (`agendarSubida`). Gana la última
  escritura: cuidado con que un dispositivo pise los cambios del otro.
- **Modo demo:** datos de práctica; no debe guardar nada real (`modoDemo`).

## Forma de trabajo (obligatoria)
1. **Modo plan primero.** Presenta el plan y espera mi aprobación antes de tocar código.
2. **Pregunta antes de asumir** reglas del negocio (precios, márgenes, crédito y abonos, qué se publica).
3. **Error repetido = asesor.** Si el mismo error o prueba falla dos veces, detente y consúltame antes del tercer intento.
4. **No leas `index.html` completo:** busca la función que necesitas (`grep`) y lee solo esa zona.
5. **Nunca** hagas commit, push ni despliegue sin mi autorización explícita.
6. **Simplicidad:** el mínimo código que resuelve lo pedido. Sin funciones, archivos ni "mejoras" que nadie pidió.
7. **Cambios quirúrgicos:** toca solo lo necesario. Lo que funciona no se reescribe ni se reordena.
8. **Si hay dos caminos razonables,** muéstralos con pros y contras antes de elegir.
9. **Define el éxito antes de empezar** (cómo sabremos que quedó bien) y no digas "listo" sin haberlo comprobado.

## Entregas chicas y con evidencia (obligatorio)
La IA genera mucho código muy rápido; nadie revisa bien 1,800 líneas de golpe. Por eso:
1. **Una entrega = un flujo.** Cada entrega cubre un solo cambio o flujo y, como guía, menos de ~400 líneas
   modificadas. Si el plan pasa de eso, divídelo en pasos numerados; cada paso se entrega y se prueba
   por separado, y no empiezas el siguiente sin mi visto bueno.
2. **Planear es diseñar, no solo listar pasos.** Si el cambio toca datos, esquema, roles, rutas o servicios
   externos, el plan explica cómo encaja con lo que ya existe: qué tablas, rutas y pantallas afecta
   y qué podría romperse.
3. **Caso real, no caso perfecto.** Diseña para el uso real (celular, red lenta, usuario con prisa),
   no para la demo. Nada de abstracciones ni opciones "por si acaso".
4. **"Listo" solo con evidencia.** Toda entrega incluye:
   - los comandos de verificación que corriste y su resultado real (no "debería pasar");
   - el recorrido del flujo como usuario real, con el rol que corresponde, paso a paso
     (con capturas si tienes navegador);
   - cuáles de los casos del punto 5 probaste;
   - **qué NO pudiste probar y por qué.** Mejor decirlo que dejarlo implícito.
5. **Casos que siempre se prueban** en lo que toques:
   - datos vacíos / primera vez que se usa;
   - error de red o servidor caído: mensaje claro y sin perder lo capturado;
   - doble clic en guardar: no duplica;
   - usuario sin permiso: no ve ni modifica lo que no le toca;
   - pantalla de celular;
   - textos con acentos y ñ.

## Verificación mínima antes de entregar
```
python -m py_compile app.py
python -c "import re,os,subprocess,tempfile;h=open('index.html',encoding='utf-8').read();p=os.path.join(tempfile.gettempdir(),'xg.js');open(p,'w',encoding='utf-8').write('\n'.join(re.findall(r'<script>(.*?)</script>',h,re.S)));subprocess.run(['node','--check',p],check=True);print('JS OK')"
```
Prueba en navegador (vista de celular) las pantallas tocadas: 0 errores en consola.

## Flujos críticos (recorrido de humo)
Después de cualquier cambio, recorre los que toque tu cambio:
1. **Producto:** alta con costo → precio sugerido correcto → aparece en Vender y en Catálogo.
2. **Venta a crédito:** vender a una clienta con abono parcial → el saldo de la venta y de la clienta cuadran.
3. **Abono posterior:** registrar otro abono → el saldo baja y el Panel lo refleja.
4. **Sincronización:** un cambio en el celular aparece en la PC (y al revés) con el PIN correcto; con PIN incorrecto se rechaza.
5. **Foto:** subir foto → `/mejorar` devuelve la imagen; si el servidor está dormido o falla, hay mensaje claro y no se traba.
6. **Post de Instagram:** se genera con los productos elegidos.
7. **Modo demo:** entrar, mover datos, salir → los datos reales quedan intactos.

## Reglas de código
- Nunca entregues fragmentos con "// resto igual": si muestras una función, que sea la función completa.
- JavaScript vanilla, sin frameworks. Python: solo lo de `requirements.txt` salvo que lo apruebe.
- Una función = un propósito. Nombres descriptivos en español, como ya usa el proyecto (`saldoClienta`, `precioSugerido`).
- Siempre: guards al inicio, null checks, debounce en botones que guardan, `try/catch` en todo `fetch`, mensajes claros en español.
- Montos en pesos (MXN) con la función `pesos` para mostrarlos; no cambies cómo se redondean sin preguntar.
- Si cambias la forma del estado, que siga leyendo los datos ya guardados (en `localStorage` y en el servidor) sin perderlos.

## Seguridad y datos
- Los datos de clientas (nombre, teléfono, saldos) son personales: no los expongas en logs ni en rutas sin PIN.
- Nunca escribas el PIN, claves ni datos reales en el código, commits o archivos.
- Secretos solo en variables de entorno de Render (`SYNC_PIN`, `DATA_DIR`).

## Despliegue
Antes de proponer un despliegue: verificación mínima limpia, flujos críticos recorridos y lista de cambios
en lenguaje simple. Nunca reemplaces el estado real con datos de demo o de prueba.
