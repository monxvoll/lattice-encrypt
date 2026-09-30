/* ==========================================================================
   Lattice Encrypt - Editor
   Sin dependencias externas: el resaltado de sintaxis se hace sobre una capa
   <pre> y el cursor real vive en un <textarea> transparente encima. Asi el
   editor sigue funcionando aunque falle la red, que es lo que importa en una
   app que se puede desplegar sin internet.
   ========================================================================== */
(function () {
  'use strict';

  var $ = function (sel) { return document.querySelector(sel); };

  // ---------------------------------------------------------------- Estado --

  // Cada linea de la muestra esta verificada contra tests/test_operadores.py.
  // TEXTO solo acepta 2 caracteres (VECTOR) o 4 (MATRIZ), por eso no hay
  // ningun ejemplo de 3. El lenguaje no admite comentarios.
  var programaInicial = [
    'VECTOR(1,2) SUMA VECTOR(3,4)',
    'MATRIZ(2,1,0,2) POR VECTOR(3,4)',
    'VECTOR(1,2) PUNTO VECTOR(2,3)',
    'VECTOR(5,7) RESTA VECTOR(2,3)',
    'VECTOR(5,7) MOD VECTOR(3,3)',
    'VECTOR(1,2) RUIDO VECTOR(0.1,0.2)',
    'VECTOR(1.4,2.6) REDONDEAR',
    'VECTOR(65,66) CARACTERES',
    'MATRIZ(72,79,76,65) CARACTERES',
    'VECTOR(0,0) TEXTO "AB"',
    'VECTOR(1,2) IGUAL VECTOR(1,2)'
  ].join('\n');

  var estado = {
    programas: [],        // { nombre, codigo, guardado, vista }
    activo: null,         // indice en programas
    vista: 'consola',     // consola | resultados | errores
    ultimoInforme: null,
    zoom: 13,
    mostrarTokens: true
  };

  var LLAVE_TOKENS = 'lattice:tokens';

  // ------------------------------------------------------- Utilidades DOM --

  function el(tag, clase, texto) {
    var n = document.createElement(tag);
    if (clase) n.className = clase;
    if (texto !== undefined && texto !== null) n.textContent = texto;
    return n;
  }

  function escapar(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function avisar(texto, tipo) {
    var caja = $('#avisos');
    var n = el('div', 'aviso' + (tipo ? ' ' + tipo : ''), texto);
    caja.appendChild(n);
    setTimeout(function () {
      n.classList.add('saliendo');
      setTimeout(function () { n.remove(); }, 200);
    }, 2800);
  }

  // ------------------------------------------------------ Resaltado Lattice --
  //
  // Las expresiones van en orden: la cadena se reconoce antes que los numeros
  // para que un " dentro de un valor no se lea de otra forma, y los numeros
  // antes que los identificadores para partir bien "1.2" en vez de "1" seguido
  // de ".2". El lenguaje no tiene comentarios, asi que "#" no se resalta.
  var OPERADORES = 'SUMA|POR|PUNTO|RESTA|MOD|RUIDO|REDONDEAR|IGUAL|TEXTO|CARACTERES|KEYGEN|CIFRAR|DESCIFRAR';
  var TIPOS = 'VECTOR|MATRIZ';

  var RE = new RegExp(
    '(?<cadena>"[^"\\n]*")' +
    '|(?<numero>\\d+(?:\\.\\d+)?)' +
    '|(?<operador>\\b(?:' + OPERADORES + ')\\b)' +
    '|(?<tipo>\\b(?:' + TIPOS + ')\\b)' +
    '|(?<signo>[(),])',
    'g'
  );

  function resaltar(texto) {
    var salida = '';
    var ultimo = 0;
    var m;
    RE.lastIndex = 0;

    while ((m = RE.exec(texto)) !== null) {
      if (m.index > ultimo) salida += escapar(texto.slice(ultimo, m.index));
      var clase = m.groups.cadena ? 'tk-cadena'
        : m.groups.numero ? 'tk-numero'
        : m.groups.operador ? 'tk-operador'
        : m.groups.tipo ? 'tk-tipo'
        : 'tk-signo';
      salida += '<span class="' + clase + '">' + escapar(m[0]) + '</span>';
      ultimo = m.index + m[0].length;
    }
    salida += escapar(texto.slice(ultimo));
    return salida;
  }

  // ---------------------------------------------------------------- Editor --

  var editor = { linea: 1 };

  function montarEditor() {
    var caja = $('#editor-caja');
    caja.textContent = '';

    var raiz = el('div', 'editor');
    var numeros = el('div', 'editor-numeros');
    numeros.setAttribute('aria-hidden', 'true');

    var area = el('div', 'editor-area');

    // Capa de color. aria-hidden porque el texto real ya esta en el textarea.
    var fondo = el('pre', 'editor-fondo');
    fondo.setAttribute('aria-hidden', 'true');

    // Capa de edicion: invisible, pero es la que tiene el foco.
    var entrada = el('textarea', 'editor-entrada');
    entrada.id = 'editor-codigo';
    entrada.setAttribute('aria-label', 'Codigo del programa');
    entrada.setAttribute('spellcheck', 'false');
    entrada.setAttribute('autocorrect', 'off');
    entrada.setAttribute('autocapitalize', 'off');
    entrada.wrap = 'off';

    area.appendChild(fondo);
    area.appendChild(entrada);
    raiz.appendChild(numeros);
    raiz.appendChild(area);
    caja.appendChild(raiz);

    editor.raiz = raiz;
    editor.numeros = numeros;
    editor.fondo = fondo;
    editor.entrada = entrada;

    entrada.addEventListener('input', function () {
      var p = programaActivo();
      if (p) {
        p.codigo = entrada.value;
        p.guardado = false;
        pintarPestanas();
      }
      pintarFondo();
      pintarNumeros(entrada.value);
      programarBorrador();
    });

    // La capa de color y la numeracion siguen al textarea.
    entrada.addEventListener('scroll', function () {
      fondo.scrollTop = entrada.scrollTop;
      fondo.scrollLeft = entrada.scrollLeft;
      numeros.scrollTop = entrada.scrollTop;
    });

    entrada.addEventListener('keydown', manejarTeclas);
    entrada.addEventListener('click', actualizarPosicion);
    entrada.addEventListener('keyup', actualizarPosicion);
    entrada.addEventListener('select', actualizarPosicion);
    document.addEventListener('selectionchange', function () {
      if (document.activeElement === entrada) actualizarPosicion();
    });
  }

  function manejarTeclas(ev) {
    var ta = editor.entrada;

    // Ctrl/Cmd+Enter: ejecutar
    if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
      ev.preventDefault();
      ejecutar();
      return;
    }
    // Ctrl/Cmd+S: guardar
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 's') {
      ev.preventDefault();
      abrirGuardar();
      return;
    }
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === '+' || ev.key === '=')) {
      ev.preventDefault();
      cambiarZoom(1);
      return;
    }
    if ((ev.ctrlKey || ev.metaKey) && ev.key === '-') {
      ev.preventDefault();
      cambiarZoom(-1);
      return;
    }

    // Tab: indentar. Shift+Tab quita la indentacion de la linea actual.
    if (ev.key === 'Tab') {
      ev.preventDefault();
      if (!ev.shiftKey) {
        indentar();
      } else {
        quitarIndentacion();
      }
      return;
    }

    // Enter: mantener la indentacion de la linea anterior.
    if (ev.key === 'Enter' && !ev.shiftKey) {
      var ini = ta.selectionStart;
      var antes = ta.value.slice(0, ini);
      var linea = antes.slice(antes.lastIndexOf('\n') + 1);
      var sangria = (linea.match(/^[ \t]*/) || [''])[0];
      if (sangria) {
        ev.preventDefault();
        insertar('\n' + sangria);
      }
    }
  }

  function insertar(texto) {
    var ta = editor.entrada;
    var ini = ta.selectionStart;
    var fin = ta.selectionEnd;
    ta.setRangeText(texto, ini, fin, 'end');
    ta.dispatchEvent(new Event('input'));
    actualizarPosicion();
  }

  /** Devuelve los limites de las lineas completas que toca la seleccion. */
  function bloqueSeleccion() {
    var ta = editor.entrada;
    var valor = ta.value;
    var ini = ta.selectionStart;
    var fin = ta.selectionEnd;
    return {
      ini: ini,
      fin: fin,
      desde: valor.lastIndexOf('\n', ini - 1) + 1,
      // Si la seleccion acaba a mitad de linea, se incluye esa linea entera:
      // indentar media linea dejaria el resto sin alinear.
      hasta: valor.indexOf('\n', fin) === -1 ? valor.length : fin,
      valor: valor
    };
  }

  function indentar() {
    var b = bloqueSeleccion();
    var solapaVariasLineas = b.valor.slice(b.ini, b.fin).indexOf('\n') !== -1;

    // Sin salto de linea se comporta como un editor normal: inserta 4 espacios.
    if (!solapaVariasLineas) {
      insertar('    ');
      return;
    }

    var bloque = b.valor.slice(b.desde, b.hasta);
    var indentado = bloque.split('\n').map(function (l) {
      return '    ' + l;
    }).join('\n');

    editor.entrada.setRangeText(indentado, b.desde, b.hasta, 'select');
    editor.entrada.dispatchEvent(new Event('input'));
    actualizarPosicion();
  }

  function quitarIndentacion() {
    var b = bloqueSeleccion();
    var bloque = b.valor.slice(b.desde, b.hasta);
    var quitado = bloque.replace(/^ {1,4}/gm, '').replace(/^\t/gm, '');
    if (quitado === bloque) return;

    editor.entrada.setRangeText(quitado, b.desde, b.hasta, 'select');
    editor.entrada.dispatchEvent(new Event('input'));
    actualizarPosicion();
  }

  function pintarFondo() {
    var texto = editor.entrada.value;
    // Exactamente el mismo texto, sin anadir saltos de linea: si el <pre>
    // tuviera uno mas, sus lineas dejarian de coincidir con las del textarea.
    editor.fondo.innerHTML = resaltar(texto);
  }

  function pintarNumeros(texto) {
    var total = texto.split('\n').length;
    var frag = document.createDocumentFragment();
    for (var i = 1; i <= total; i++) {
      frag.appendChild(el('div', i === editor.linea ? 'actual' : '', String(i)));
    }
    editor.numeros.textContent = '';
    editor.numeros.appendChild(frag);
    editor.numeros.scrollTop = editor.entrada.scrollTop;
  }

  function actualizarPosicion() {
    var ta = editor.entrada;
    if (document.activeElement !== ta) return;

    var texto = ta.value;
    var num = ta.selectionStart;
    var antes = texto.slice(0, num);
    var linea = antes.split('\n').length;
    var col = num - (antes.lastIndexOf('\n') + 1) + 1;

    if (linea !== editor.linea) {
      editor.linea = linea;
      pintarNumeros(texto);
    }

    $('#estado-pos').textContent = 'Ln ' + linea + ', Col ' + col;
  }

  function actualizarContador() {
    var total = editor.entrada.value.split('\n').length;
    $('#estado-lineas').textContent = plural(total, 'linea', 'lineas');
  }

  /** Vuelca el codigo del programa activo al editor y refresca las capas. */
  function sincronizar() {
    var p = programaActivo();
    var texto = p ? p.codigo : '';

    if (editor.entrada.value !== texto) editor.entrada.value = texto;
    editor.linea = 1;

    pintarFondo();
    pintarNumeros(texto);
    actualizarContador();
    $('#estado-pos').textContent = 'Ln 1, Col 1';
  }

  function plural(n, uno, muchos) {
    return n + ' ' + (n === 1 ? uno : muchos);
  }

  // El borrador se guarda con retardo: al pegar un archivo entero se dispara
  // un 'input' por linea y sin esto se escribirian cientos de veces.
  var temporizadorBorrador = null;

  function programarBorrador() {
    clearTimeout(temporizadorBorrador);
    temporizadorBorrador = setTimeout(function () {
      var p = programaActivo();
      if (!p) return;
      try {
        if (p.codigo.trim()) {
          localStorage.setItem('lattice:borrador', JSON.stringify({
            nombre: p.nombre,
            codigo: p.codigo
          }));
        } else {
          localStorage.removeItem('lattice:borrador');
        }
      } catch (e) {}
    }, 400);
  }

  // ------------------------------------------------------------- Programas --

  function programaActivo() {
    return estado.activo === null ? null : estado.programas[estado.activo];
  }

  function nuevoPrograma(codigo, nombre) {
    estado.programas.push({
      nombre: nombre || 'programa' + (estado.programas.length + 1),
      codigo: codigo === undefined ? '' : codigo,
      guardado: false,
      vista: true
    });
    estado.activo = estado.programas.length - 1;
    pintarPestanas();
    sincronizar();
  }

  function pintarPestanas() {
    var cont = $('#tabs-programas');
    cont.textContent = '';

    estado.programas.forEach(function (p, i) {
      var tab = el('button', 'tab-archivo' + (i === estado.activo ? ' activa' : ''));
      tab.type = 'button';
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-selected', String(i === estado.activo));
      tab.title = p.nombre + '.le';
      tab.appendChild(el('span', null, p.nombre + '.le'));

      if (!p.guardado) tab.appendChild(el('span', 'modificado'));

      var x = el('button', 'tab-cerrar');
      x.type = 'button';
      x.title = 'Cerrar';
      x.setAttribute('aria-label', 'Cerrar ' + p.nombre);
      x.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" fill="none"/></svg>';
      x.addEventListener('click', function (ev) {
        ev.stopPropagation();
        cerrarPrograma(i);
      });

      tab.appendChild(x);
      tab.addEventListener('click', function () {
        estado.activo = i;
        pintarPestanas();
        sincronizar();
      });
      cont.appendChild(tab);
    });
  }

  function cerrarPrograma(indice) {
    var p = estado.programas[indice];
    if (!p) return;

    if (!p.guardado) {
      confirmar(
        'Cerrar "' + p.nombre + '"',
        'Este programa tiene cambios sin guardar y se perderan.',
        function () { quitarPrograma(indice); }
      );
      return;
    }
    quitarPrograma(indice);
  }

  function quitarPrograma(indice) {
    var wasActive = estado.activo === indice;
    estado.programas.splice(indice, 1);
    limpiarBorrador(indice);

    if (estado.programas.length === 0) {
      nuevoPrograma();
    } else {
      if (wasActive) {
        estado.activo = Math.min(indice, estado.programas.length - 1);
      } else if (indice < estado.activo) {
        estado.activo -= 1;
      }
      pintarPestanas();
      sincronizar();
    }
  }

  function limpiarBorrador(indice) {
    try {
      var b = JSON.parse(localStorage.getItem('lattice:borrador') || 'null');
      if (b && estado.programas[indice] && b.nombre === estado.programas[indice].nombre) {
        localStorage.removeItem('lattice:borrador');
      }
    } catch (e) {}
  }

  // ------------------------------------------------------------------ API --

  function pedir(ruta, opciones) {
    return fetch(ruta, opciones).then(function (r) {
      return r.json().catch(function () {
        return {};
      }).then(function (cuerpo) {
        if (!r.ok) {
          throw new Error(cuerpo.detail || cuerpo.error || ('HTTP ' + r.status));
        }
        return cuerpo;
      });
    });
  }

  // -------------------------------------------------------------- Ejecutar --

  function ejecutar() {
    var p = programaActivo();
    if (!p) return;

    var boton = $('#btn-ejecutar');
    if (boton.getAttribute('aria-busy') === 'true') return;

    boton.setAttribute('aria-busy', 'true');
    ponerIndicador('Ejecutando...', 'corre');
    mostrarVacio(false);

    pedir('/ejecutar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codigo: p.codigo, tokens: estado.mostrarTokens })
    })
      .then(function (informe) {
        pintarInforme(informe);
        ponerIndicador(
          informe.ok ? 'Ejecucion correcta' : plural(informe.errores, 'error', 'errores'),
          informe.ok ? 'ok' : 'mal'
        );
        $('#estado-duracion').textContent = informe.duracion_ms + ' ms';
      })
      .catch(function (err) {
        pintarErrorConexion(err.message);
        ponerIndicador('Error de conexion', 'mal');
      })
      .then(function () {
        boton.removeAttribute('aria-busy');
      });
  }

  function ponerIndicador(texto, clase) {
    var n = $('#estado-indicador');
    n.textContent = texto;
    n.className = 'estado-indicador' + (clase ? ' ' + clase : '');
  }

  function mostrarVacio(mostrar) {
    $('#salida-vacia').hidden = !mostrar;
  }

  function pintarInforme(informe) {
    estado.ultimoInforme = informe;

    // --- Consola: lo que el interprete escribio, tal cual ---
    var consola = $('#vista-consola');
    if (informe.consola && informe.consola.trim()) {
      consola.textContent = informe.consola.replace(/\n+$/, '');
    } else {
      consola.textContent = '';
    }
    consola.scrollTop = consola.scrollHeight;

    // --- Resultados: una ficha por linea ejecutada ---
    var contR = $('#vista-resultados');
    contR.textContent = '';
    if (!informe.lineas.length) {
      contR.appendChild(el('p', 'vacio-sub', 'El programa no tenia instrucciones.'));
    }
    informe.lineas.forEach(function (l) { contR.appendChild(fichaLinea(l)); });

    // --- Errores: solo las que fallaron ---
    var malas = informe.lineas.filter(function (l) { return !l.ok; });
    var contE = $('#vista-errores');
    contE.textContent = '';
    var pastilla = $('#pastilla-errores');
    if (malas.length) {
      pastilla.hidden = false;
      pastilla.textContent = String(malas.length);
      malas.forEach(function (l) { contE.appendChild(fichaLinea(l)); });
    } else {
      pastilla.hidden = true;
      contE.appendChild(el('p', 'vacio-sub', 'Ninguna linea fallo.'));
    }

    mostrarVacio(false);

    // Si hubo errores, mirar esa pestana sola es lo util.
    if (malas.length) cambiarVista('errores');
  }

  function fichaLinea(l) {
    var ficha = el('div', 'fila ' + (l.ok ? 'ok' : 'mal'));
    ficha.appendChild(el('div', 'fila-num', 'L' + l.linea));
    ficha.appendChild(el('div', 'fila-codigo', l.codigo));

    if (!l.ok) {
      var err = el('div', 'fila-error');
      err.appendChild(document.createTextNode(l.error));
      if (l.tipo) err.appendChild(el('span', 'fila-tipo', l.tipo));
      ficha.appendChild(err);
      return ficha;
    }

    if (Object.prototype.hasOwnProperty.call(l, 'resultado')) {
      ficha.appendChild(el('div', 'valor ' + claseValor(l.resultado), formatear(l.resultado)));
    }

    if (l.tokens && l.tokens.length) {
      var det = el('details');
      det.style.gridColumn = '1 / -1';
      var sum = el('summary', null, l.tokens.length + ' token' + (l.tokens.length === 1 ? '' : 's'));
      sum.style.cssText = 'cursor:pointer;font-size:11.5px;color:var(--apagado-texto);padding-left:22px';
      det.appendChild(sum);
      det.appendChild(tablaTokens(l.tokens, l.tokens_recortados));
      ficha.appendChild(det);
    }

    return ficha;
  }

  function claseValor(v) {
    if (typeof v === 'boolean') return 'booleano';
    if (typeof v === 'string') return 'cadena';
    return '';
  }

  function formatear(v) {
    if (Array.isArray(v)) return '[' + v.map(formatear).join(', ') + ']';
    if (typeof v === 'string') return JSON.stringify(v);
    return String(v);
  }

  function tablaTokens(tokens, recortados) {
    var pre = el('pre', 'tokens');
    tokens.forEach(function (t, i) {
      if (i) pre.appendChild(document.createTextNode('\n'));
      pre.appendChild(el('span', 'token-tipo', t.tipo));
      pre.appendChild(document.createTextNode('  '));
      pre.appendChild(el('span', 'token-valor', JSON.stringify(t.valor)));
    });
    if (recortados) {
      pre.appendChild(document.createTextNode('\n... (lista truncada)'));
    }
    return pre;
  }

  function pintarErrorConexion(mensaje) {
    estado.ultimoInforme = null;
    $('#vista-consola').textContent = 'No se pudo contactar al servidor: ' + mensaje;
    $('#vista-resultados').textContent = '';
    $('#vista-errores').textContent = '';
    $('#pastilla-errores').hidden = true;
    mostrarVacio(false);
    cambiarVista('consola');
  }

  function cambiarVista(nombre) {
    estado.vista = nombre;
    ['consola', 'resultados', 'errores'].forEach(function (v) {
      $('#vista-' + v).hidden = v !== nombre;
      var t = document.querySelector('.tab[data-vista="' + v + '"]');
      if (t) {
        t.classList.toggle('activa', v === nombre);
        t.setAttribute('aria-selected', String(v === nombre));
      }
    });
    // Al mirar por primera vez hay contenido, asi que el estado vacio sobra.
    if (estado.ultimoInforme) mostrarVacio(false);
  }

  // ------------------------------------------------------- Guardar / abrir --

  function abrirGuardar() {
    var p = programaActivo();
    if (!p) return;
    var input = $('#input-nombre');
    input.value = p.nombre;
    $('#error-guardar').hidden = true;
    $('#velo-guardar').hidden = false;
    input.focus();
    input.select();
  }

  function guardar() {
    var p = programaActivo();
    if (!p) return;

    var nombre = $('#input-nombre').value.trim();
    var err = $('#error-guardar');

    if (!/^[A-Za-z0-9_\-]{1,64}$/.test(nombre)) {
      err.textContent = 'Usa de 1 a 64 caracteres: letras, numeros, guion o guion bajo.';
      err.hidden = false;
      input.focus();
      return;
    }

    $('#btn-confirmar-guardar').disabled = true;
    pedir('/api/programas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre: nombre, codigo: p.codigo })
    })
      .then(function () {
        p.nombre = nombre;
        p.guardado = true;
        $('#velo-guardar').hidden = true;
        pintarPestanas();
        avisar('Guardado como ' + nombre + '.le', 'exito');
        refrescarMenuProgramas();
      })
      .catch(function (e) {
        err.textContent = e.message;
        err.hidden = false;
      })
      .then(function () {
        $('#btn-confirmar-guardar').disabled = false;
      });
  }

  function cargarProgramas() {
    return pedir('/api/programas')
      .then(function (r) { return r.programas || []; })
      .catch(function () { return []; });
  }

  function refrescarMenuProgramas() {
    return cargarProgramas().then(function (nombres) {
      var menu = $('#menu-programas');
      if (!menu) return;
      menu.textContent = '';
      var acciones = $('#tabs-programas').parentElement.querySelector('.tabs-acciones');
      acciones.parentElement.appendChild(menu);

      if (!nombres.length) {
        menu.appendChild(el('div', 'menu-nota', 'Todavia no hay programas guardados.'));
        return;
      }

      nombres.forEach(function (nombre) {
        var item = el('div', 'menu-item');
        item.setAttribute('role', 'option');
        item.tabIndex = 0;
        item.appendChild(el('span', 'punto-lenguaje'));
        item.appendChild(el('span', null, nombre + '.le'));

        var borrar = el('button', 'tab-cerrar');
        borrar.type = 'button';
        borrar.title = 'Borrar del servidor';
        borrar.setAttribute('aria-label', 'Borrar ' + nombre);
        borrar.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24"><path d="M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
        borrar.addEventListener('click', function (ev) {
          ev.stopPropagation();
          confirmar('Borrar ' + nombre + '.le', 'Se eliminara del servidor. No se puede deshacer.', function () {
            pedir('/api/programas/' + encodeURIComponent(nombre), { method: 'DELETE' })
              .then(function () {
                avisar('Borrado ' + nombre + '.le');
                refrescarMenuProgramas();
              })
              .catch(function (e) { avisar(e.message, 'error'); });
          });
        });

        item.appendChild(borrar);
        item.addEventListener('click', function () { abrirGuardado(nombre); });
        item.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); abrirGuardado(nombre); }
        });
        menu.appendChild(item);
      });
    });
  }

  function abrirGuardado(nombre) {
    pedir('/api/programas/' + encodeURIComponent(nombre))
      .then(function (r) {
        // Si ya esta abierto, solo se activa en vez de duplicarlo.
        var i = estado.programas.findIndex(function (p) { return p.nombre === nombre; });
        if (i >= 0) {
          estado.activo = i;
          pintarPestanas();
          sincronizar();
        } else {
          nuevoPrograma(r.codigo, nombre);
          estado.programas[estado.activo].guardado = true;
          pintarPestanas();
        }
        cerrarMenu();
        avisar('Abierto ' + nombre + '.le');
      })
      .catch(function (e) { avisar(e.message, 'error'); });
  }

  // ------------------------------------------------------------ Dialogos --

  var pendienteConfirmar = null;

  function confirmar(titulo, texto, alAceptar) {
    $('#titulo-confirmar').textContent = titulo;
    $('#texto-confirmar').textContent = texto;
    pendienteConfirmar = alAceptar;
    $('#velo-confirmar').hidden = false;
    $('#btn-confirmar-aceptar').focus();
  }

  function cerrarDialogos() {
    $('#velo-guardar').hidden = true;
    $('#velo-ayuda').hidden = true;
    $('#velo-confirmar').hidden = true;
    pendienteConfirmar = null;
  }

  // ----------------------------------------------------------------- Menus --

  function cerrarMenu() {
    $('#menu-lenguaje').hidden = true;
    $('#btn-lenguaje').setAttribute('aria-expanded', 'false');
    var mp = $('#menu-programas');
    if (mp) {
      mp.hidden = true;
      $('#btn-menu-programas').setAttribute('aria-expanded', 'false');
    }
  }

  function alternarMenu(boton, menu) {
    var abrir = menu.hidden;
    cerrarMenu();
    menu.hidden = !abrir;
    boton.setAttribute('aria-expanded', String(abrir));
  }

  // ---------------------------------------------------------------- Tema --

  function pintarBotonTema() {
    var oscuro = document.documentElement.classList.contains('dark');
    $('#btn-tema').innerHTML = oscuro
      ? '<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>'
      : '<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" fill="none"/></svg>';
  }

  function alternarTema() {
    var oscuro = !document.documentElement.classList.contains('dark');
    document.documentElement.className = oscuro ? 'dark' : 'light';
    try { localStorage.setItem('lattice:tema', oscuro ? 'dark' : 'light'); } catch (e) {}
    pintarBotonTema();
  }

  function aplicarZoom() {
    document.documentElement.style.setProperty('--tam-fuente', estado.zoom + 'px');
  }

  function cambiarZoom(paso) {
    estado.zoom = Math.min(22, Math.max(11, estado.zoom + paso));
    aplicarZoom();
    pintarNumeros(editor.entrada.value);
  }

  // ------------------------------------------------------------ Divisor --

  function montarDivisor() {
    var div = $('#divisor');
    var arrastrando = false;

    function mover(clientX) {
      var cuerpo = $('.cuerpo').getBoundingClientRect();
      var pct = ((clientX - cuerpo.left) / cuerpo.width) * 100;
      $('#panel-editor').style.flex = '0 0 ' + acotar(pct) + '%';
    }

    div.addEventListener('mousedown', function (ev) {
      arrastrando = true;
      div.classList.add('arrastrando');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      ev.preventDefault();
    });

    window.addEventListener('mousemove', function (ev) {
      if (arrastrando) mover(ev.clientX);
    });

    window.addEventListener('mouseup', function () {
      if (!arrastrando) return;
      arrastrando = false;
      div.classList.remove('arrastrando');
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    });

    // Accesible con teclado: cada flecha mueve el divisor 2 puntos porcentuales.
    div.addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
      ev.preventDefault();
      var cuerpo = $('.cuerpo').getBoundingClientRect();
      var actualPct = ($('#panel-editor').getBoundingClientRect().width / cuerpo.width) * 100;
      var paso = ev.key === 'ArrowLeft' ? -2 : 2;
      $('#panel-editor').style.flex = '0 0 ' + acotar(actualPct + paso) + '%';
    });
  }

  function acotar(pct) {
    return Math.min(85, Math.max(15, pct));
  }

  // ----------------------------------------------------------------- Arranque --

  function enlazar() {
    $('#btn-ejecutar').addEventListener('click', ejecutar);
    $('#btn-tema').addEventListener('click', alternarTema);
    $('#btn-ayuda').addEventListener('click', function () { $('#velo-ayuda').hidden = false; });
    $('#btn-cerrar-ayuda').addEventListener('click', function () { $('#velo-ayuda').hidden = true; });
    $('#btn-docs').addEventListener('click', function () { $('#velo-ayuda').hidden = false; });

    $('#btn-lenguaje').addEventListener('click', function () {
      alternarMenu($('#btn-lenguaje'), $('#menu-lenguaje'));
    });

    $('#btn-menu-programas').addEventListener('click', function (ev) {
      ev.stopPropagation();
      refrescarMenuProgramas().then(function () {
        var m = $('#menu-programas');
        if (m) alternarMenu($('#btn-menu-programas'), m);
      });
    });

    $('#btn-nuevo').addEventListener('click', function () {
      nuevoPrograma('');
      editor.entrada.focus();
    });

    $('#btn-limpiar').addEventListener('click', function () {
      var p = programaActivo();
      if (!p || (!p.codigo && !p.guardado)) return;
      confirmar('Limpiar el editor', 'Se borrara el codigo de "' + p.nombre + '".', function () {
        p.codigo = '';
        p.guardado = false;
        pintarPestanas();
        sincronizar();
        editor.entrada.focus();
      });
    });

    $('#btn-guardar').addEventListener('click', abrirGuardar);
    $('#btn-cancelar-guardar').addEventListener('click', function () { $('#velo-guardar').hidden = true; });
    $('#btn-confirmar-guardar').addEventListener('click', guardar);
    $('#input-nombre').addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') { ev.preventDefault(); guardar(); }
    });

    $('#btn-limpiar-salida').addEventListener('click', function () {
      estado.ultimoInforme = null;
      $('#vista-consola').textContent = '';
      $('#vista-resultados').textContent = '';
      $('#vista-errores').textContent = '';
      $('#pastilla-errores').hidden = true;
      $('#estado-duracion').textContent = '';
      mostrarVacio(true);
      ponerIndicador('Listo', '');
    });

    $('#btn-cancelar-confirmar').addEventListener('click', function () { $('#velo-confirmar').hidden = true; });
    $('#btn-confirmar-aceptar').addEventListener('click', function () {
      var f = pendienteConfirmar;
      $('#velo-confirmar').hidden = true;
      if (f) f();
    });

    $('#btn-tokens').addEventListener('click', function () {
      estado.mostrarTokens = !estado.mostrarTokens;
      this.setAttribute('aria-pressed', String(estado.mostrarTokens));
      try { localStorage.setItem(LLAVE_TOKENS, estado.mostrarTokens ? '1' : '0'); } catch (e) {}
      avisar(estado.mostrarTokens ? 'Los tokens se mostraran al ejecutar' : 'Los tokens quedaran ocultos');
    });

    $('#btn-zoom-mas').addEventListener('click', function () { cambiarZoom(1); });
    $('#btn-zoom-menos').addEventListener('click', function () { cambiarZoom(-1); });
    $('#btn-formato').addEventListener('click', function () { estado.zoom = 13; aplicarZoom(); });

    document.querySelectorAll('.tab[data-vista]').forEach(function (t) {
      t.addEventListener('click', function () { cambiarVista(t.dataset.vista); });
    });

    document.addEventListener('click', function (ev) {
      if (!ev.target.closest('.selector-lenguaje') && !ev.target.closest('#menu-programas')) {
        cerrarMenu();
      }
    });

    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') { cerrarDialogos(); cerrarMenu(); }
    });

    // Avisa antes de perder el trabajo no guardado.
    window.addEventListener('beforeunload', function (ev) {
      var alguno = estado.programas.some(function (p) { return !p.guardado; });
      if (alguno) { ev.preventDefault(); ev.returnValue = ''; }
    });
  }

  function cargarPreferencias() {
    try {
      var t = localStorage.getItem('lattice:tokens');
      if (t !== null) estado.mostrarTokens = t === '1';
    } catch (e) {}
    $('#btn-tokens').setAttribute('aria-pressed', String(estado.mostrarTokens));
  }

  function recuperarBorrador() {
    try {
      var b = JSON.parse(localStorage.getItem('lattice:borrador') || 'null');
      if (b && typeof b.codigo === 'string' && b.codigo.trim()) {
        return b;
      }
    } catch (e) {}
    return null;
  }

  function iniciar() {
    pintarBotonTema();
    aplicarZoom();
    montarEditor();
    montarDivisor();
    enlazar();
    cargarPreferencias();

    var borrador = recuperarBorrador();
    if (borrador) {
      nuevoPrograma(borrador.codigo, borrador.nombre);
      avisar('Recuperado tu borrador anterior');
    } else {
      nuevoPrograma(programaInicial, 'ejemplo');
      estado.programas[0].guardado = false;
      pintarPestanas();
    }

    mostrarVacio(true);
    ponerIndicador('Listo', '');

    refrescarMenuProgramas();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
