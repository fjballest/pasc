# Cómo instalar y usar pasc

`pasc` es la herramienta que usamos en la asignatura para compilar y
ejecutar programas en Pascal. Esta guía explica, paso a paso y sin dar
nada por supuesto, cómo instalarla en Windows, macOS o Linux y cómo
comprobar que funciona.

Hay tres formas de instalarla. Elige **una**:

1. **Con el instalador** (recomendado). Es lo más sencillo: descargas un
   archivo, lo abres y sigues los pasos.
2. **Con el zip portable.** No instala nada en el sistema: descomprimes una
   carpeta y ejecutas pasc desde ella. Sirve, por ejemplo, en un ordenador
   en el que no puedes instalar programas o desde un pendrive.
3. **Con el zip de código fuente.** Funciona en cualquier sistema, pero
   necesitas tener Python 3.7 o posterior instalado. Úsalo solo si las otras
   dos formas no te funcionan.

Ninguna de las dos primeras formas necesita Python ni ningún otro programa.

---

## Índice

- [Antes de empezar: conceptos básicos](#antes-de-empezar-conceptos-básicos)
- [Descargar pasc](#descargar-pasc)
- [Opción 1: instalador](#opción-1-instalador)
  - [Windows](#windows-con-el-instalador)
  - [macOS](#macos-con-el-instalador)
  - [Linux](#linux-con-el-instalador)
- [Opción 2: zip portable](#opción-2-zip-portable)
  - [Windows](#windows-con-el-zip-portable)
  - [macOS](#macos-con-el-zip-portable)
  - [Linux](#linux-portable)
- [Opción 3: zip de código fuente](#opción-3-zip-de-código-fuente)
- [Tu primer programa](#tu-primer-programa)
- [Cómo se usa pasc](#cómo-se-usa-pasc)
- [Problemas frecuentes](#problemas-frecuentes)
- [Desinstalar](#desinstalar)

---

## Antes de empezar: conceptos básicos

### Qué es un terminal

`pasc` no tiene ventanas ni botones: se usa escribiendo órdenes en un
**terminal** (también llamado consola o línea de comandos). Es una ventana
en la que escribes una orden, pulsas **Intro** y el ordenador la ejecuta.

Cómo abrir un terminal:

- **Windows:** pulsa la tecla **Windows**, escribe `terminal` (en Windows
  10 antiguos, escribe `cmd`) y pulsa **Intro**. Se abre una ventana negra
  o azul con algo como `C:\Users\tunombre>`. Eso es el terminal. En Windows
  7 se llama **Símbolo del sistema** y está en *Inicio → Todos los
  programas → Accesorios*.
- **macOS:** pulsa **Cmd + Espacio**, escribe `terminal` y pulsa **Intro**.
  También está en *Aplicaciones → Utilidades → Terminal*.
- **Linux:** pulsa **Ctrl + Alt + T**, o busca «Terminal» en el menú de
  aplicaciones.

En esta guía, cuando veas un recuadro como este:

```
pasc --version
```

significa que tienes que **escribir esa orden en el terminal y pulsar
Intro**. Escríbela exactamente igual, respetando espacios, mayúsculas y
minúsculas.

### Qué es la carpeta actual

El terminal siempre está «dentro» de una carpeta, la **carpeta actual**.
Cuando ejecutas `pasc hola.p`, pasc busca `hola.p` en esa carpeta. Para
cambiar de carpeta se usa la orden `cd` («change directory»):

```
cd Documentos
```

entra en la carpeta `Documentos`, y

```
cd ..
```

sube a la carpeta que la contiene. Para ver qué hay en la carpeta actual,
escribe `dir` en Windows o `ls` en macOS y Linux.

Un truco útil en todos los sistemas: escribe `cd ` (con un espacio
detrás), **arrastra la carpeta** desde el explorador de archivos hasta la
ventana del terminal (así se escribe su ruta completa) y pulsa **Intro**.

### Qué versión de tu sistema tienes

- **Windows:** pulsa **Windows + R**, escribe `winver` y pulsa Intro.
  pasc funciona en Windows 7, 8, 10 y 11, de 64 bits.
- **macOS:** menú de la manzana (arriba a la izquierda) → *Acerca de este Mac*. pasc funciona en macOS 10.13
  (High Sierra) o posterior, tanto en Mac con procesador Intel como en Mac
  con Apple silicon (M1, M2, M3...).
- **Linux:** pasc funciona en ordenadores de 64 bits (x86_64) con cualquier
  distribución publicada desde 2017 aproximadamente (Ubuntu 18.04 o
  posterior, Debian 9 o posterior, Fedora, Mint, etc.). Para comprobarlo,
  ejecuta `uname -m` en un terminal: debe responder `x86_64`.

---

## Descargar pasc

1. Abre en el navegador la página de versiones de pasc:
   **https://github.com/fjballest/pasc/releases**
2. Arriba aparece la versión más reciente (por ejemplo, **v1.0**). Busca
   la sección **Assets** y, si hace falta, pulsa sobre ella para ver la
   lista de archivos.
3. Descarga **solo** el archivo que necesitas, según tu sistema y la opción
   que hayas elegido. En los nombres, `1.0` es el número de versión; puede
   ser otro.

| Sistema | Instalador (opción 1) | Zip portable (opción 2) |
|---|---|---|
| Windows | `pasc-1.0-windows-setup.exe` | `pasc-1.0-windows-portable.zip` |
| macOS | `pasc-1.0-macos.pkg` | `pasc-1.0-macos-portable.zip` |
| Linux | `pasc-1.0-linux-x86_64.tar.gz` | el mismo `pasc-1.0-linux-x86_64.tar.gz` |
| Cualquiera (opción 3) | `pasc-1.0-source.zip` | |

El archivo se guarda normalmente en la carpeta **Descargas**.

---

## Opción 1: instalador

### Windows con el instalador

1. Abre la carpeta **Descargas** y haz doble clic en
   `pasc-1.0-windows-setup.exe`.
2. Es posible que Windows muestre una ventana azul que dice **«Windows
   protegió su PC»**. Aparece porque el instalador no está firmado
   digitalmente, no porque sea peligroso. Pulsa **Más información** y
   después **Ejecutar de todas formas**.
3. Si el navegador avisa de que el archivo «no se descarga habitualmente»,
   elige **Conservar** (en Edge: botón **···** → *Conservar* → *Mostrar más*
   → *Conservar de todas formas*).
4. Se abre el asistente de instalación. Pulsa **Instalar** (o **Install**)
   y, al terminar, **Finalizar** (**Finish**). No hace falta ser
   administrador: pasc se instala solo para tu usuario, en
   `C:\Users\tunombre\AppData\Local\Programs\pasc`.
5. El instalador añade pasc a la lista de programas que el terminal
   encuentra solo (la variable **PATH**). Para que tenga efecto, **cierra
   todos los terminales que tuvieras abiertos y abre uno nuevo**.
6. Comprueba que funciona. En el terminal nuevo escribe:

   ```
   pasc --version
   ```

   Debe aparecer algo como `pasc 1.0`. Si aparece «no se reconoce como un
   comando», consulta [Problemas frecuentes](#problemas-frecuentes).

Ya está. Sigue en [Tu primer programa](#tu-primer-programa).

### macOS con el instalador

1. Abre la carpeta **Descargas** y haz doble clic en `pasc-1.0-macos.pkg`.
2. Lo más probable es que macOS diga que **no puede abrirlo porque es de
   un desarrollador no identificado** (el paquete no está firmado). No es
   un problema. Hazlo así:
   - **macOS 14 (Sonoma) o anterior:** cierra el aviso, haz **clic derecho**
     (o Ctrl + clic) sobre el archivo `.pkg`, elige **Abrir** y, en el nuevo
     aviso, pulsa **Abrir**.
   - **macOS 15 (Sequoia) o posterior:** cierra el aviso, abre
     **Ajustes del Sistema → Privacidad y seguridad**, baja hasta el final,
     donde pone que se ha bloqueado `pasc-1.0-macos.pkg`, y pulsa **Abrir
     igualmente**. Vuelve a hacer doble clic en el archivo y confirma con
     **Abrir**.
3. Se abre el instalador de macOS. Pulsa **Continuar** y luego
   **Instalar**. Te pedirá la **contraseña de tu usuario del Mac** (la que
   usas para entrar en el ordenador); escríbela y pulsa **Instalar
   software**. Al final, pulsa **Cerrar**. Si pregunta si quieres mover el
   instalador a la papelera, puedes decir que sí.
4. pasc queda instalado en `/usr/local/bin/pasc`, una carpeta que el
   terminal ya conoce. Abre un terminal **nuevo** y escribe:

   ```
   pasc --version
   ```

   Debe aparecer `pasc 1.0`.

Funciona igual en Mac con procesador Intel y con Apple silicon (M1, M2...):
el paquete contiene las dos versiones y se usa la adecuada automáticamente.

Ya está. Sigue en [Tu primer programa](#tu-primer-programa).

### Linux con el instalador

En Linux, el «instalador» es un archivo comprimido con un guion que copia
pasc en tu carpeta personal. No hace falta ser administrador.

1. Abre un terminal y entra en la carpeta de descargas:

   ```
   cd ~/Descargas
   ```

   (Si tu sistema está en inglés, la carpeta se llama `Downloads`:
   `cd ~/Downloads`).
2. Descomprime el archivo:

   ```
   tar xzf pasc-1.0-linux-x86_64.tar.gz
   ```

   Se crea la carpeta `pasc-1.0-linux-x86_64`.
3. Entra en ella y ejecuta el instalador:

   ```
   cd pasc-1.0-linux-x86_64
   ./install.sh
   ```

   Debe responder `pasc installed in /home/tunombre/.local/bin/pasc`.
4. Si además aparece un mensaje que dice **«Add /home/tunombre/.local/bin to
   your PATH»**, tu sistema todavía no busca programas en esa carpeta.
   Normalmente basta con **cerrar la sesión y volver a entrar** (en Ubuntu,
   Debian y Mint esa carpeta se añade sola si existe al iniciar sesión). Si
   aun así no funciona, ejecuta esta orden una sola vez y abre un terminal
   nuevo:

   ```
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
   ```

   (Si usas **zsh**, cambia `~/.profile` por `~/.zshrc`).
5. Comprueba que funciona:

   ```
   pasc --version
   ```

Si prefieres instalarlo para todos los usuarios del ordenador, en el paso 3
usa `sudo ./install.sh /usr/local` (te pedirá tu contraseña).

Cuando hayas terminado, puedes borrar el archivo `.tar.gz` y la carpeta
`pasc-1.0-linux-x86_64`.

Ya está. Sigue en [Tu primer programa](#tu-primer-programa).

---

## Opción 2: zip portable

El zip portable contiene pasc listo para usar, sin instalar nada. La
diferencia con el instalador es que el terminal no lo encuentra solo:
tienes que indicarle dónde está, o añadirlo tú al PATH (se explica abajo).

### Windows con el zip portable

1. Crea una carpeta para pasc, por ejemplo `C:\Users\tunombre\pasc` (en el
   Explorador de archivos: carpeta de tu usuario → clic derecho → *Nuevo →
   Carpeta* → llámala `pasc`).
2. Haz clic derecho en `pasc-1.0-windows-portable.zip` → **Extraer todo...**
   → pulsa **Examinar**, elige la carpeta `pasc` que acabas de crear y pulsa
   **Extraer**. Dentro debe quedar el archivo `pasc.exe` junto a otros
   archivos que necesita (no los borres ni los separes de `pasc.exe`).
3. Abre un terminal y comprueba que funciona escribiendo la ruta completa
   de `pasc.exe`:

   ```
   C:\Users\tunombre\pasc\pasc.exe --version
   ```

   (cambia `tunombre` por tu nombre de usuario; con el truco de arrastrar el
   archivo `pasc.exe` a la ventana del terminal se escribe solo).
4. Para ejecutar un programa, escribe esa misma ruta seguida del nombre del
   programa:

   ```
   C:\Users\tunombre\pasc\pasc.exe hola.p
   ```

**Opcional: usar solo `pasc`.** Para no tener que escribir la ruta entera,
añade la carpeta al PATH de tu usuario:

1. Pulsa **Windows**, escribe `variables de entorno` y abre **Editar las
   variables de entorno de esta cuenta**.
2. En la parte de arriba (*Variables de usuario*), selecciona **Path** y
   pulsa **Editar...** (si no existe, pulsa **Nueva...** y llámala `Path`).
3. Pulsa **Nuevo**, escribe `C:\Users\tunombre\pasc` y pulsa **Aceptar** en
   todas las ventanas.
4. Abre un terminal nuevo: ya puedes escribir `pasc --version`.

Si usas pasc desde un **pendrive**, extrae el zip en una carpeta del
pendrive y usa la ruta correspondiente (por ejemplo,
`E:\pasc\pasc.exe hola.p`).

### macOS con el zip portable

1. Haz doble clic en `pasc-1.0-macos-portable.zip` (en **Descargas**). Se
   crea una carpeta llamada `pasc`.
2. Mueve esa carpeta a un sitio fijo, por ejemplo a tu carpeta personal
   (en Finder: menú *Ir → Inicio*, y arrastra allí la carpeta `pasc`).
3. macOS marca como «en cuarentena» todo lo que viene de Internet y no
   dejaría ejecutarlo. Para quitar esa marca, abre un terminal y escribe:

   ```
   xattr -dr com.apple.quarantine ~/pasc
   ```

   (no responde nada si todo va bien).
4. Comprueba que funciona:

   ```
   ~/pasc/pasc --version
   ```
5. Para ejecutar un programa:

   ```
   ~/pasc/pasc hola.p
   ```

**Opcional: usar solo `pasc`.** Ejecuta una vez:

```
echo 'export PATH="$HOME/pasc:$PATH"' >> ~/.zshrc
```

y abre un terminal nuevo. (En macOS 10.14 o anterior, el terminal usa
**bash**: escribe `~/.bash_profile` en lugar de `~/.zshrc`).

### Linux portable

En Linux, el archivo `pasc-1.0-linux-x86_64.tar.gz` sirve también como
versión portable:

1. Descomprímelo donde quieras (por ejemplo, en tu carpeta personal o en un
   pendrive):

   ```
   cd ~
   tar xzf ~/Descargas/pasc-1.0-linux-x86_64.tar.gz
   ```
2. pasc está en `pasc-1.0-linux-x86_64/pasc/pasc`. Compruébalo:

   ```
   ~/pasc-1.0-linux-x86_64/pasc/pasc --version
   ```
3. Para ejecutar un programa:

   ```
   ~/pasc-1.0-linux-x86_64/pasc/pasc hola.p
   ```

**Opcional: usar solo `pasc`.** Ejecuta una vez esta orden y abre un
terminal nuevo:

```
echo 'export PATH="$HOME/pasc-1.0-linux-x86_64/pasc:$PATH"' >> ~/.profile
```

---

## Opción 3: zip de código fuente

pasc está escrito en Python, así que puede ejecutarse directamente desde
su código fuente en cualquier ordenador que tenga **Python 3.7 o
posterior**. Es la opción que hay que usar, por ejemplo, en un Linux que no
sea de 64 bits x86 (una Raspberry Pi, un portátil ARM...).

### Paso 1: comprobar o instalar Python

Abre un terminal y escribe:

- **Windows:** `py --version`
- **macOS y Linux:** `python3 --version`

Si responde `Python 3.7` o un número mayor (`Python 3.12.4`, por ejemplo),
ya lo tienes: pasa al paso 2. Si no, instálalo:

- **Windows:** descarga Python de **https://www.python.org/downloads/** y
  ejecuta el instalador. En la primera pantalla **marca la casilla «Add
  python.exe to PATH»** y pulsa **Install Now**. En Windows 7 u 8, la
  última versión que funciona es Python 3.8: búscala en
  https://www.python.org/downloads/windows/ («Windows installer (64-bit)»).
- **macOS:** descarga el instalador para macOS de
  **https://www.python.org/downloads/** y ábrelo (doble clic → Continuar →
  Instalar). También sirve escribir `xcode-select --install` en el
  terminal, que instala las herramientas de desarrollo de Apple, Python 3
  incluido.
- **Linux:** casi todas las distribuciones lo traen. Si no, instálalo con
  el gestor de paquetes. Por ejemplo, en Ubuntu o Debian:

  ```
  sudo apt install python3
  ```

  y en Fedora: `sudo dnf install python3`.

Abre un terminal **nuevo** y vuelve a comprobar la versión.

### Paso 2: descomprimir el código

1. Descarga `pasc-1.0-source.zip` de la página de versiones.
2. Descomprímelo en un sitio fijo, por ejemplo en tu carpeta personal
   (Windows: clic derecho → *Extraer todo...*; macOS: doble clic; Linux:
   `unzip pasc-1.0-source.zip`). Se crea una carpeta `pasc-1.0` que
   contiene, entre otros, el archivo `pasc.py`.

### Paso 3: ejecutar pasc

Hay que pedir a Python que ejecute `pasc.py`, indicando dónde está:

- **Windows:**

  ```
  py C:\Users\tunombre\pasc-1.0\pasc.py --version
  py C:\Users\tunombre\pasc-1.0\pasc.py hola.p
  ```

  La carpeta también trae `pasc.bat`, que hace lo mismo:
  `C:\Users\tunombre\pasc-1.0\pasc.bat hola.p`. Si añades la carpeta
  `pasc-1.0` al PATH (como en la [opción 2 para
  Windows](#windows-con-el-zip-portable)), podrás escribir solo
  `pasc hola.p`.

- **macOS y Linux:**

  ```
  python3 ~/pasc-1.0/pasc.py --version
  python3 ~/pasc-1.0/pasc.py hola.p
  ```

  La carpeta también trae un guion llamado `pasc`:
  `~/pasc-1.0/pasc hola.p`. Para escribir solo `pasc`, añade la carpeta al
  PATH:

  ```
  echo 'export PATH="$HOME/pasc-1.0:$PATH"' >> ~/.zshrc
  ```

  (en Linux, o en un Mac con bash, usa `~/.profile` en lugar de `~/.zshrc`)
  y abre un terminal nuevo.

---

## Tu primer programa

Vamos a comprobar que todo funciona con un programa de verdad.

1. Crea una carpeta para tus programas, por ejemplo `pascal` dentro de
   **Documentos**.
2. Abre un editor de **texto plano** (no Word ni Pages, que añaden formato):
   - Windows: **Bloc de notas** (o Visual Studio Code, Notepad++...).
   - macOS: **TextEdit**, pero antes elige *Formato → Convertir a texto
     sin formato*. Mejor aún, Visual Studio Code o BBEdit.
   - Linux: el editor de texto de tu escritorio (gedit, Kate...) o
     Visual Studio Code.
3. Escribe este programa:

   ```pascal
   {$mode objfpc}{$H-}{$R+}{$T+}{$Q+}{$V+}{$D+}{$X-}{$warnings on}
   program hola;
   var
   	nombre: string;
   begin
   	write('¿Cómo te llamas? ');
   	readln(nombre);
   	writeln('Hola, ', nombre, '!');
   end.
   ```
4. Guárdalo en tu carpeta `pascal` con el nombre **`hola.p`**. Cuidado:
   - El Bloc de notas tiende a añadir `.txt`. En *Guardar como*, elige
     *Tipo: Todos los archivos* y escribe `hola.p`.
   - TextEdit puede preguntar si quieres usar `.txt`: elige **Usar .p**.
5. Abre un terminal y entra en esa carpeta (con `cd` y el truco de
   arrastrar la carpeta a la ventana):

   ```
   cd Documentos/pascal
   ```

   (en Windows: `cd Documents\pascal`, o el nombre que tenga en tu
   sistema).
6. Ejecuta el programa:

   ```
   pasc hola.p
   ```

   (o la ruta completa de pasc, si usas la versión portable o el código
   fuente). Escribe tu nombre, pulsa Intro y debería saludarte.

Si te equivocas al escribir el programa, pasc te dice dónde está el error,
con el nombre del archivo, la línea y la columna. Por ejemplo:

```
hola.p:6:9: error: Identifier not found "nombr"
```

significa: en `hola.p`, línea 6, columna 9, hay un nombre que no está
declarado. Corrige el programa en el editor, guárdalo y vuelve a ejecutar
`pasc hola.p`.

---

## Cómo se usa pasc

La forma general es:

```
pasc [opciones] programa.p
```

pasc compila el programa y, si no hay errores, lo ejecuta. Opciones útiles:

| Orden | Qué hace |
|---|---|
| `pasc prog.p` | compila y ejecuta `prog.p` |
| `pasc -c prog.p` | solo comprueba si el programa tiene errores, sin ejecutarlo |
| `pasc -w prog.p` | además avisa de problemas de estilo: líneas largas, procedimientos demasiado largos, código repetido, nombres mal escritos... |
| `pasc -g prog.p` | permite declarar variables globales antes de los procedimientos y funciones (normalmente deben ir justo antes del programa principal) |
| `pasc -z prog.p` | las variables sin inicializar valen 0 en vez de basura aleatoria |
| `pasc --version` | muestra la versión de pasc |

Algunas cosas que conviene saber:

- **Las variables sin inicializar contienen basura.** Si tu programa usa
  una variable antes de darle valor, cada ejecución puede dar un resultado
  distinto. No es un fallo de pasc: es un fallo del programa.
- **Errores en ejecución.** Si el programa hace algo incorrecto (dividir
  por cero, salirse de un array...), se detiene y explica qué ha pasado y
  dónde, por ejemplo `Runtime error 201 at prog.p:12: Range check error`.
- **Para depurar**, puedes escribir `stack();` en cualquier punto del
  programa: pasc mostrará los procedimientos y funciones en curso con el
  valor de sus parámetros y variables locales, además de las variables
  globales. `stack(1)`, `stack(2)`... muestran cada vez más detalle: los
  registros y arrays campo a campo, con sangrado, y siguen los punteros.
- **Memoria dinámica.** Al terminar, pasc avisa de la memoria reservada con
  `new` que no se ha liberado con `dispose`.
- **Datos de entrada desde un archivo.** Para que el programa lea de un
  archivo en lugar del teclado:

  ```
  pasc prog.p < datos.txt
  ```
- **Para parar un programa** que no termina (por ejemplo, un bucle
  infinito), pulsa **Ctrl + C** en el terminal.

---

## Ver cómo se ejecuta un programa: pascdb

`pascdb` viene con pasc y sirve para ver, paso a paso, qué hace un programa:

```
pascdb hola.p
```

Se abre una página en el navegador (si no se abre sola, copia en el
navegador la dirección que aparece en el terminal). En ella ves:

- el programa, con la línea que se va a ejecutar resaltada;
- **Datos**: las variables dibujadas como cajas (registros, arrays y listas
  enlazadas, con flechas para los punteros). Pulsa la cabecera de un
  registro o array para plegarlo o desplegarlo; los parámetros `var` se dibujan como
  una flecha al argumento (o, con el botón de arriba, como una copia
  atenuada);
- **Pila**: la pila tal y como está en memoria, con las direcciones de
  retorno de cada llamada;
- **Memoria**: toda la memoria en uso, byte a byte, con el nombre de cada
  variable. Lo que está por encima del puntero de pila (`sp ▶`) aparece
  atenuado: ya no se usa, pero sigue ahí;
- **Ficheros**: los ficheros abiertos para leer (y la entrada estándar),
  con lo ya leído atenuado y el siguiente carácter que se leerá resaltado;
- la salida del programa y una línea para escribir su entrada.

En cada paso se resalta lo que ha cambiado (en Datos, Pila y Memoria) y
cada panel se desplaza para que se vea.

El botón **EN**/**ES** cambia el idioma de la página (inglés o español).

El botón ⧉ de Datos, Pila, Memoria o Ficheros abre esa parte en otra
ventana, y **Juntos** las muestra a la vez, una al lado de otra.

Botones: **Paso** (o la tecla Intro) ejecuta una línea, entrando en los
procedimientos y funciones; **Reproducir** (o la barra espaciadora) lo
ejecuta despacio él solo, a la velocidad que elijas; **Continuar** sigue
hasta el siguiente punto de parada (se ponen pulsando el número de una
línea) o hasta el final; **Reiniciar** vuelve a empezar. Para terminar,
pulsa **Salir** (o **Ctrl + C** en el terminal).

---

## Problemas frecuentes

**Windows: «"pasc" no se reconoce como un comando interno o externo».**
El terminal no encuentra pasc.
- Si usaste el instalador: cierra **todos** los terminales y abre uno nuevo.
  Si sigue sin funcionar, cierra la sesión de Windows y vuelve a entrar.
- Si usas el zip portable: escribe la ruta completa
  (`C:\Users\tunombre\pasc\pasc.exe`) o añade la carpeta al PATH como se
  explica arriba.

**macOS o Linux: «command not found: pasc» o «pasc: orden no encontrada».**
- Con el instalador de macOS: abre un terminal nuevo. Comprueba que existe
  `/usr/local/bin/pasc` con `ls /usr/local/bin/pasc`.
- Con el instalador de Linux: cierra la sesión y vuelve a entrar, o sigue el
  paso 4 de la [instalación en Linux](#linux-con-el-instalador).
- Con el zip portable o el código: usa la ruta completa o añade la carpeta al
  PATH.

**macOS: «no se puede abrir porque es de un desarrollador no identificado»
o «Apple no puede comprobar que no contiene software malicioso».**
Ocurre porque pasc no está firmado por Apple. Sigue el paso 2 de la
[instalación en macOS](#macos-con-el-instalador). Con el zip portable,
ejecuta `xattr -dr com.apple.quarantine ~/pasc`.

**Linux: «Permission denied» al ejecutar `./install.sh` o pasc.**
Los permisos se pierden si descomprimiste el archivo con un programa
gráfico antiguo. Descomprímelo con `tar xzf` como se indica, o ejecuta
`chmod +x install.sh pasc/pasc`.

**Linux: «version `GLIBC_2.xx' not found».**
Tu distribución es anterior a 2017. Usa la [opción 3 (código
fuente)](#opción-3-zip-de-código-fuente).

**«pasc: hola.p: No such file or directory».**
pasc no encuentra el programa en la carpeta actual. Comprueba con `dir`
(Windows) o `ls` (macOS y Linux) que el archivo está ahí y que se llama
exactamente `hola.p`, no `hola.p.txt`. En Windows, para ver las extensiones
en el Explorador: menú *Vista → Mostrar → Extensiones de nombre de archivo*.

**Los acentos o la «ñ» salen mal en Windows.**
Guarda los programas en el editor con codificación UTF-8 y, en el
terminal, ejecuta antes `chcp 65001`.

**El antivirus bloquea o borra pasc.exe.**
Algunos antivirus desconfían de los programas nuevos no firmados. Restaura
el archivo desde la cuarentena del antivirus y márcalo como de confianza,
o usa la opción 3.

---

## Desinstalar

- **Windows (instalador):** *Configuración → Aplicaciones → Aplicaciones
  instaladas* (o *Panel de control → Programas*), busca **pasc** y pulsa
  **Desinstalar**.
- **macOS (instalador):** en un terminal:

  ```
  sudo rm -rf /usr/local/lib/pasc /usr/local/bin/pasc
  ```
- **Linux (instalador):** en un terminal:

  ```
  rm -rf ~/.local/lib/pasc ~/.local/bin/pasc
  ```

  (si lo instalaste para todos: `sudo rm -rf /usr/local/lib/pasc /usr/local/bin/pasc`).
- **Zip portable o código fuente:** borra la carpeta donde lo
  descomprimiste y, si la añadiste al PATH, quita esa línea o entrada.
