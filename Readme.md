# Lectura/Escritura de tags STRING en PLC Rockwell: Node-RED vs Python

Cuando se trabaja con tags de tipo `STRING` en un PLC Rockwell (Logix), hay que
recordar que internamente no es un string plano, sino una estructura:

```
STRING
├── LEN  (DINT)          → longitud actual del texto
└── DATA (SINT[82])      → caracteres en ASCII
```

Esto afecta cómo cada herramienta lee y escribe el dato. A continuación se
explican las dos opciones principales.

---

## Opción 1: Node-RED (nodos CIP / EtherNet-IP)

### Cómo funciona

Nodos como `node-red-contrib-cip-ethernet-ip` no interpretan el `STRING` como
texto: devuelven el **buffer crudo** de la estructura completa (LEN + DATA).

Ejemplo de lo que llega en `msg.payload` al leer un STRING:

```json
[11,0,0,0,72,111,108,97,32,109,117,110,100,111,33,0,0,0, ...]
```

- Los primeros 4 bytes son el `LEN` (entero de 32 bits, little-endian).
- El resto son los caracteres ASCII, rellenados con ceros hasta 82 bytes.

### Lectura (Function node)

```javascript
let buf = Buffer.from(msg.payload);
let len = buf.readInt32LE(0);
let str = buf.slice(4, 4 + len).toString('ascii');

msg.payload = str;
return msg;
```

### Escritura (Function node)

```javascript
let texto = "Adios mundo";
let buf = Buffer.alloc(86); // 4 bytes LEN + 82 bytes DATA
buf.writeInt32LE(texto.length, 0);
buf.write(texto, 4, 'ascii');

msg.payload = Array.from(buf);
return msg;
```

### Ventajas

- Se integra directamente en un flujo Node-RED existente (dashboards, MQTT,
  bases de datos, lógica visual).
- Bueno para prototipado rápido y orquestación de múltiples protocolos a la vez.

### Desventajas

- No maneja tipos complejos (como `STRING`) de forma nativa: hay que
  decodificar/codificar manualmente los bytes.
- Comportamiento y formato de datos varían según el nodo/paquete npm usado.
- Manejo de errores menos claro (depende del nodo).

---

## Opción 2: Python (librería `pylogix`)

### Qué es

`pylogix` es una librería de Python creada específicamente para comunicarse
con PLCs Rockwell/Logix (ControlLogix, CompactLogix, Micro800, etc.) usando
el protocolo EtherNet/IP. Es prácticamente un estándar de facto en integración
industrial con Python.

Instalación:

```bash
pip install pylogix
```

### Sintaxis básica

**Lectura:**

```python
from pylogix import PLC

with PLC('192.168.1.10') as comm:
    ret = comm.Read('MiTagString')
    print(ret.Value)   # -> "Hola mundo!" (ya decodificado)
    print(ret.Status)  # -> "Success" si todo salió bien
```

**Escritura:**

```python
from pylogix import PLC

with PLC('192.168.1.10') as comm:
    ret = comm.Write('MiTagString', 'Adios mundo')
    print(ret.Status)  # -> "Success" o mensaje de error
```

No es necesario manejar `LEN`, `DATA`, bytes ni padding manualmente: la
librería reconoce el tipo `STRING` y hace la conversión automáticamente.

### Otras capacidades útiles

```python
# Leer múltiples tags a la vez
ret = comm.Read(['Tag1', 'Tag2', 'Tag3'])

# Leer un tag dentro de un programa (scope local)
ret = comm.Read('Program:MainProgram.MiTagString')

# Leer un array
ret = comm.Read('MiArray', 10)  # lee 10 elementos desde MiArray[0]

# Obtener info del PLC (nombre, tipo, etc.)
info = comm.GetPLCTime()
```

### Ventajas

- Maneja tipos complejos (`STRING`, UDTs, arrays multidimensionales) de forma
  nativa, sin decodificación manual.
- Manejo de errores explícito vía `ret.Status`.
- Documentación y comunidad orientadas específicamente a Rockwell.
- Código más corto y legible para tareas de lectura/escritura.

### Desventajas

- Si el resto del proyecto vive en Node-RED, agregar Python implica un
  componente aparte que hay que comunicar (HTTP, MQTT, `exec` node, etc.).
- Menos adecuado si se necesita orquestación visual o integración rápida con
  muchos protocolos distintos a la vez.

---

## Resumen / Cuándo usar cada uno

| Escenario | Recomendación |
|---|---|
| El proyecto es principalmente comunicación con PLCs Rockwell (lecturas/escrituras como núcleo) | **Python + pylogix** |
| Node-RED ya es la plataforma central (dashboards, IoT, MQTT) y el PLC es solo una fuente de datos más | **Node-RED**, o un microservicio en Python expuesto por HTTP/MQTT que Node-RED consuma |
| Se necesita prototipar rápido con múltiples protocolos | **Node-RED** |
| Se trabaja mucho con tipos de datos complejos (STRING, UDTs) | **Python + pylogix** |

Una arquitectura híbrida también es válida: un microservicio en Python
(por ejemplo con Flask o FastAPI) que use `pylogix` para hablar con el PLC,
y Node-RED consumiendo esos datos vía HTTP o MQTT como capa de orquestación.

## Para ejecutar desde Docker:

Crear la imagen: 
> docker build -t mi_app .

Desplegar el contenedor:
> docker run -d --name mi_contenedor --restart unless-stopped -p 8501:8501 mi_app