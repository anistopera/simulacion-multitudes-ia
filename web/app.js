'use strict';
// El navegador solo dibuja y envía controles; toda la lógica vive en Python.

const $ = (id) => document.getElementById(id);
const lienzo = $('lienzo');
const ctx = lienzo.getContext('2d', { alpha: false });
const SONDEO_MIN_MS = 50;       // como máximo 20 consultas por segundo
const DPR_MAX = 1.5;            // más resolución no se nota y calienta la GPU
const TIPO = { ruido: 0, frontera: 1, nucleo: 2 };

let cfg = null;                 // mapa (de /config)
let est = null;                 // último estado (de /estado)
let escala = 1;                 // píxeles del canvas por metro
let dpr = 1;
let ordenes = 0;                // descarta respuestas de /estado anteriores a una orden
let resumenOculto = false;
let avisoTimer = 0;
let avisoFijo = false;          // error o desconexión: dura hasta que se resuelva
const capas = { calor: false, grupos: false, rutas: false };
let rutas = new Map();          // id -> waypoints [x, y]; vacío si la capa está apagada
let rutasV = -1;                // versión de rutas recibida

// Capas estáticas: se regeneran solo al cambiar el tamaño.
const fondo = document.createElement('canvas');   // piso y cuadrícula
const frente = document.createElement('canvas');  // paredes, entrada y salida

// Calor: una celda de 2 m = un píxel. Se mezcla entre la matriz anterior y la nueva.
const calor = document.createElement('canvas');   // mezcla actual
const calorA = document.createElement('canvas');  // matriz anterior
const calorB = document.createElement('canvas');  // matriz nueva
let calorSeg = -1, calorInicio = 0, calorFin = 0, mezcla = -1;

// Movimiento: se dibuja un instante en el pasado, entre dos estados con hora del servidor.
let estados = [];               // [{ r: hora en ms, agentes, porId }]
let desfase = 0;                // hora del navegador - hora del servidor
let intervalos = [];            // ms entre estados
let tardanzas = [];             // ms que tarda en llegar cada estado
let retraso = 120;              // ms de margen para tener siempre el estado siguiente
let pendiente = true, cuadroPedido = false, animaba = false, ultimoCuadro = 0;
const FUNDIDO_MS = 250;         // aparición de los peatones en un episodio nuevo
let fundidoInicio = -Infinity;

// ---- Metros -> píxeles. Origen (0, 0) abajo a la izquierda; el canvas lo tiene arriba. ----
const px = (x) => x * escala;
const py = (y) => (cfg.alto - y) * escala;
const num = (v, d = 1) => v.toFixed(d).replace('.', ',');
const limitar = (v, a, b) => Math.max(a, Math.min(b, v));

// Rampa rojo -> amarillo -> verde según q = velocidad real / deseada (101 tonos).
let RAMPA = [];
let T = {};                     // colores del tema actual, leídos de las variables CSS

function leerTema() {
  const css = getComputedStyle(document.documentElement);
  const v = (n) => css.getPropertyValue(`--${n}`).trim();
  const hex = (h) => { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
  const lista = (n) => v(n).split(',').map(Number);
  const [rojo, amarillo, verde] = ['rojo', 'amarillo', 'verde'].map((n) => hex(v(n)));
  RAMPA = Array.from({ length: 101 }, (_, i) => {
    const q = i / 100;
    const [a, b, t] = q < 0.5 ? [rojo, amarillo, q * 2] : [amarillo, verde, (q - 0.5) * 2];
    return `rgb(${a.map((c, k) => Math.round(c + (b[k] - c) * t)).join(',')})`;
  });
  T = {
    piso: v('lienzo-piso'), rejilla: v('lienzo-rejilla'), pared: v('pared'), texto: v('lienzo-texto'),
    entrada: v('entrada'), salida: v('salida'), entradaTexto: v('entrada-texto'), salidaTexto: v('salida-texto'),
    etiqueta: v('etiqueta-fondo'), neutro: v('neutro'), ruta: v('ruta'), borde: v('peaton-borde'),
    ruido: v('ruido'), cruz: v('cruz'), contorno: v('cruz-contorno'),
    calorIni: lista('calor-ini'), calorFin: lista('calor-fin'), calorAlfa: Number(v('calor-alfa')),
  };
}

function alternarAtajos() {
  const raiz = document.documentElement, visibles = raiz.dataset.atajos !== 'si';
  if (visibles) raiz.dataset.atajos = 'si'; else delete raiz.dataset.atajos;
  $('atajos').setAttribute('aria-checked', visibles);
  try { localStorage.setItem('atajos', visibles ? 'si' : 'no'); } catch (e) { /* sin almacenamiento */ }
}

function cambiarTema() {
  const raiz = document.documentElement, claro = raiz.dataset.tema !== 'claro';
  if (claro) raiz.dataset.tema = 'claro'; else delete raiz.dataset.tema;
  $('tema').setAttribute('aria-checked', claro);
  try { localStorage.setItem('tema', claro ? 'claro' : 'oscuro'); } catch (e) { /* sin almacenamiento */ }
  leerTema();
  if (cfg) prepararCapas();
  if (est) { pintarCalor(); copiarCalor(calorB); calorInicio = calorFin = 0; mezcla = -1; }
  pendiente = true;
  pedirCuadro();
}
const colorVelocidad = (q) => RAMPA[Math.round(limitar(q, 0, 1) * 100)];

// ---- Capas estáticas ----
function prepararCapas() {
  const w = lienzo.width, h = lienzo.height;
  fondo.width = frente.width = w;
  fondo.height = frente.height = h;

  const f = fondo.getContext('2d');
  f.fillStyle = T.piso;
  f.fillRect(0, 0, w, h);
  f.strokeStyle = T.rejilla;
  f.lineWidth = Math.max(1, Math.round(dpr));
  f.beginPath();
  for (let x = 2; x < cfg.ancho; x += 2) { const p = Math.round(px(x)) + 0.5; f.moveTo(p, 0); f.lineTo(p, h); }
  for (let y = 2; y < cfg.alto; y += 2) { const p = Math.round(py(y)) + 0.5; f.moveTo(0, p); f.lineTo(w, p); }
  f.stroke();

  const g = frente.getContext('2d');
  g.fillStyle = T.pared;
  for (const [x, y] of cfg.obstaculos) {       // bordes redondeados a píxel: sin costuras
    const izq = Math.round(px(x)), der = Math.round(px(x + cfg.tam_celda));
    const arriba = Math.round(py(y + cfg.tam_celda)), abajo = Math.round(py(y));
    g.fillRect(izq, arriba, der - izq, abajo - arriba);
  }
  g.font = `${Math.round(Math.max(10, escala * 0.36))}px system-ui, sans-serif`;
  for (const [p, color] of [[cfg.entrada, T.entrada], [cfg.salida, T.salida]]) {
    g.strokeStyle = color;
    g.lineWidth = Math.max(2, escala * 0.09);
    g.beginPath();
    g.arc(px(p[0]), py(p[1]), escala * 0.48, 0, 2 * Math.PI);
    g.stroke();
  }
  g.fillStyle = T.texto;
  g.textAlign = 'left';
  g.textBaseline = 'bottom';
  g.fillText('(0, 0)', Math.round(escala * 0.15), h - Math.round(escala * 0.1));
}

function ajustarLienzo() {
  if (!cfg) return;
  dpr = Math.min(window.devicePixelRatio || 1, DPR_MAX);
  const w = Math.max(1, Math.round(lienzo.clientWidth * dpr));
  const h = Math.max(1, Math.round(w * cfg.alto / cfg.ancho));
  if (w === lienzo.width && h === lienzo.height && fondo.width === w) return;
  lienzo.width = w;
  lienzo.height = h;
  escala = w / cfg.ancho;
  prepararCapas();
  pendiente = true;
  pedirCuadro();
}
new ResizeObserver(ajustarLienzo).observe(lienzo);

// Avisa al mover la ventana a una pantalla con otra escala.
function vigilarEscala() {
  matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`).addEventListener('change', () => {
    ajustarLienzo();
    vigilarEscala();
  }, { once: true });
}

// ---- Calor ----
function pintarCalor() {                       // solo cuando llega una matriz nueva
  const m = est.densidad;
  if (!m.length) return;
  const c = calorB.getContext('2d');
  const img = c.createImageData(calorB.width, calorB.height);
  for (let f = 0; f < m.length; f++) {
    for (let col = 0; col < m[f].length; col++) {
      const i = Math.min(1, m[f][col] / 4);    // satura en 4 personas/m²
      const k = 4 * ((m.length - 1 - f) * calorB.width + col);   // fila 0 = abajo
      for (let canal = 0; canal < 3; canal++) {
        img.data[k + canal] = T.calorIni[canal] + (T.calorFin[canal] - T.calorIni[canal]) * i;
      }
      img.data[k + 3] = T.calorAlfa * Math.pow(i, 0.8);
    }
  }
  c.putImageData(img, 0, 0);
}

function copiarCalor(origen) {
  const c = calorA.getContext('2d');
  c.clearRect(0, 0, calorA.width, calorA.height);
  c.drawImage(origen, 0, 0);
}

function mezclarCalor(ahora) {                 // dos copias sobre un canvas de 15 x 10
  const k = calorFin > calorInicio ? limitar((ahora - calorInicio) / (calorFin - calorInicio), 0, 1) : 1;
  if (k === mezcla) return;
  mezcla = k;
  const c = calor.getContext('2d');
  c.clearRect(0, 0, calor.width, calor.height);
  c.globalCompositeOperation = 'lighter';
  c.globalAlpha = 1 - k;
  c.drawImage(calorA, 0, 0);
  c.globalAlpha = k;
  c.drawImage(calorB, 0, 0);
  c.globalAlpha = 1;
  c.globalCompositeOperation = 'source-over';
}

// ---- Dibujo de un cuadro ----
function tramo(R) {                            // los dos estados que rodean al instante R
  const n = estados.length;
  let i = 0;
  while (i < n - 2 && estados[i + 1].r <= R) i++;
  const a = estados[i], b = estados[Math.min(i + 1, n - 1)];
  return [a, b, a === b ? 1 : limitar((R - a.r) / (b.r - a.r), 0, 1)];
}

function dibujarRutas(R) {
  if (!rutas.size || !estados.length) return;
  const [a, b, k] = tramo(R);
  ctx.beginPath();
  for (const fila of (k >= 1 ? b.agentes : a.agentes)) {
    const ruta = rutas.get(fila[0]);
    if (!ruta || !ruta.length) continue;
    const sig = k < 1 ? b.porId.get(fila[0]) : null;
    const x = sig ? fila[1] + (sig[1] - fila[1]) * k : fila[1];
    const y = sig ? fila[2] + (sig[2] - fila[2]) * k : fila[2];
    // Las rutas llegan cada segundo: se omiten los puntos que el agente ya pasó.
    let cercano = 0, mejor = Infinity;
    for (let i = 0; i < Math.min(5, ruta.length); i++) {
      const d = (ruta[i][0] - x) ** 2 + (ruta[i][1] - y) ** 2;
      if (d < mejor) { mejor = d; cercano = i; }
    }
    ctx.moveTo(px(x), py(y));
    for (let i = Math.min(cercano + 1, ruta.length - 1); i < ruta.length; i++) {
      ctx.lineTo(px(ruta[i][0]), py(ruta[i][1]));
    }
  }
  ctx.strokeStyle = T.ruta;
  ctx.lineWidth = Math.max(1, dpr);
  ctx.stroke();
}

function dibujarAgentes(R) {
  if (!estados.length) return;
  const [a, b, k] = tramo(R);
  const radio = escala * 0.25;                 // radio físico: 0,25 m
  const borde = Math.max(1, dpr);
  const sinIniciar = est.t === 0;
  ctx.globalAlpha = limitar((performance.now() - fundidoInicio) / FUNDIDO_MS, 0, 1);

  for (const fila of (k >= 1 ? b.agentes : a.agentes)) {
    const sig = k < 1 ? b.porId.get(fila[0]) : null;
    const x = sig ? fila[1] + (sig[1] - fila[1]) * k : fila[1];
    const y = sig ? fila[2] + (sig[2] - fila[2]) * k : fila[2];
    const q = sig ? fila[3] + (sig[3] - fila[3]) * k : fila[3];
    const tipo = sig ? sig[4] : fila[4];
    const color = sinIniciar ? T.neutro : colorVelocidad(q);
    const cx = px(x), cy = py(y);

    if (capas.grupos && tipo === TIPO.ruido) {
      const d = radio * 0.72;
      ctx.strokeStyle = T.ruido;
      ctx.lineWidth = Math.max(1.5, escala * 0.06);
      ctx.beginPath();
      ctx.moveTo(cx - d, cy - d); ctx.lineTo(cx + d, cy + d);
      ctx.moveTo(cx + d, cy - d); ctx.lineTo(cx - d, cy + d);
      ctx.stroke();
      continue;
    }
    ctx.beginPath();
    ctx.arc(cx, cy, radio, 0, 2 * Math.PI);
    if (capas.grupos && tipo === TIPO.frontera) {
      ctx.strokeStyle = color;
      ctx.lineWidth = Math.max(1.5, escala * 0.07);
      ctx.stroke();
    } else {
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = T.borde;
      ctx.lineWidth = borde;
      ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;
}

function dibujarCentros() {
  const d = escala * 0.42;
  ctx.font = `600 ${Math.round(Math.max(10, escala * 0.4))}px system-ui, sans-serif`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'bottom';
  for (const [x, y, tamano] of est.centros) {
    const cx = px(x), cy = py(y);
    for (const [color, ancho] of [[T.contorno, Math.max(4, escala * 0.17)], [T.cruz, Math.max(2, escala * 0.07)]]) {
      ctx.strokeStyle = color;
      ctx.lineWidth = ancho;
      ctx.beginPath();
      ctx.moveTo(cx - d, cy); ctx.lineTo(cx + d, cy);
      ctx.moveTo(cx, cy - d); ctx.lineTo(cx, cy + d);
      ctx.stroke();
    }
    ctx.lineWidth = Math.max(3, escala * 0.12);
    ctx.strokeStyle = T.contorno;
    ctx.fillStyle = T.cruz;
    ctx.strokeText(tamano, cx + d * 0.7, cy - d * 0.3);
    ctx.fillText(tamano, cx + d * 0.7, cy - d * 0.3);
  }
}

// Arriba del anillo: queda pegada a él, sin tapar su centro ni salirse por el borde cercano.
function dibujarEtiquetas() {
  const alto = Math.round(Math.max(15, escala * 0.56));
  ctx.font = `500 ${Math.round(alto * 0.68)}px system-ui, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (const [p, color, texto] of [[cfg.entrada, T.entradaTexto, 'Entrada'], [cfg.salida, T.salidaTexto, 'Salida']]) {
    const ancho = Math.ceil(ctx.measureText(texto).width) + alto * 0.6;
    const cx = limitar(px(p[0]), ancho / 2 + 2, lienzo.width - ancho / 2 - 2);
    const arriba = Math.round(py(p[1] + 0.62)) - alto;
    ctx.fillStyle = T.etiqueta;
    ctx.fillRect(Math.round(cx - ancho / 2), arriba, Math.round(ancho), alto);
    ctx.fillStyle = color;
    ctx.fillText(texto, cx, arriba + alto / 2 + 1);
  }
}

function dibujar(R) {
  ctx.drawImage(fondo, 0, 0);
  if (!est) return;
  if (capas.calor && est.activos > 0 && est.densidad.length) {
    mezclarCalor(performance.now());
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(calor, 0, 0, lienzo.width, lienzo.height);
  }
  ctx.drawImage(frente, 0, 0);
  if (capas.rutas) dibujarRutas(R);
  dibujarAgentes(R);
  if (capas.grupos) dibujarCentros();
  dibujarEtiquetas();
}

// Solo se pide un cuadro si algo cambió o hay una animación en curso.
function pedirCuadro() {
  if (!cuadroPedido) { cuadroPedido = true; requestAnimationFrame(cuadro); }
}

function cuadro(ahora) {
  cuadroPedido = false;
  if (!cfg || !est || lienzo.width <= 1) return;
  const margen = est.fase === 'corriendo' ? retraso : 100;
  const R = ahora - desfase - margen;
  const ultimo = estados.length ? estados[estados.length - 1].r : -Infinity;
  const anima = R < ultimo || (capas.calor && ahora < calorFin) || ahora < fundidoInicio + FUNDIDO_MS;
  if (animaba && !anima) pendiente = true;     // último cuadro, en la posición exacta
  animaba = anima;
  const minimo = est.velocidad === 4 ? 0 : 1000 / 30 - 4;   // 30 fps a x1 y x2; 60 a x4
  if (pendiente || (anima && ahora - ultimoCuadro >= minimo)) {
    dibujar(R);
    ultimoCuadro = ahora;
    pendiente = false;
  }
  if (anima) pedirCuadro();
}

// ---- Panel: solo toca el DOM si el valor cambió ----
const NOMBRES = { listo: 'Listo', corriendo: 'Corriendo', pausado: 'Pausado', terminado: 'Terminado', error: 'Error' };

function poner(id, valor) {
  const e = $(id), texto = String(valor);
  if (e.textContent !== texto) e.textContent = texto;
}

function ocultar(id, oculto) {
  if ($(id).hidden !== oculto) $(id).hidden = oculto;
}

function deshabilitar(e, valor) {
  if (e.disabled !== valor) e.disabled = valor;
}

function marcar(selector, atributo, valor) {
  for (const b of document.querySelectorAll(selector)) {
    const activo = String(b.dataset[atributo] === String(valor));
    if (b.getAttribute('aria-pressed') !== activo) b.setAttribute('aria-pressed', activo);
  }
}

function actualizarPanel() {
  const e = est;
  if ($('indicador').className !== e.fase) $('indicador').className = e.fase;
  poner('indicador-txt', NOMBRES[e.fase]);
  const lento = e.fase === 'corriendo' && e.velocidad_real < e.velocidad * 0.9;
  poner('contexto', `${e.escenario} · ${e.total} agentes · modo ${e.modo.replace('_', '+')} · semilla ${e.semilla} · x${e.velocidad}`
    + (lento ? ` (real x${num(e.velocidad_real)})` : ''));
  poner('m-activos', e.activos);
  poner('m-llegados', e.llegados);
  poner('m-total', ` / ${e.total}`);
  poner('m-tiempo', num(e.t));
  poner('m-criticas', e.criticas);

  marcar('[data-modo]', 'modo', e.modo);
  marcar('[data-escenario]', 'escenario', e.escenario);
  marcar('[data-semilla]', 'semilla', e.semilla);
  marcar('[data-velocidad]', 'velocidad', e.velocidad);
  deshabilitar(document.querySelector('[data-modo="B_PSO"]'), !e.pso.disponible);
  ocultar('nota-pso', e.pso.disponible);
  poner('nota-pso', `B+PSO no disponible: ${e.pso.motivo}.`);

  poner('btn-iniciar-txt', { corriendo: 'Pausa', pausado: 'Continuar' }[e.fase] || 'Iniciar');
  deshabilitar($('btn-iniciar'), e.fase === 'terminado' || e.fase === 'error');
  deshabilitar($('btn-paso'), e.fase !== 'listo' && e.fase !== 'pausado');

  if (e.error) mostrarAviso(`Error en la simulación: ${e.error}. Pulsa Reiniciar.`, true, 0);
  if (!e.resumen) resumenOculto = false;
  ocultar('resumen', !e.resumen || resumenOculto);
  if (e.resumen) {
    poner('res-llegados', `${e.resumen.llegados}/${e.resumen.total}`);
    poner('res-tiempo', `${num(e.resumen.tiempo)} s`);
    poner('res-tasa', `${num(e.resumen.tasa)} %`);
  }
}

function mostrarAviso(texto, esError = false, duracion = 2600) {
  clearTimeout(avisoTimer);
  avisoFijo = !duracion;
  poner('aviso', texto);
  $('aviso').className = esError ? 'error' : '';
  ocultar('aviso', false);
  if (duracion) avisoTimer = setTimeout(() => { $('aviso').hidden = true; }, duracion);
}

// Guarda el estado con la hora del servidor y prepara movimiento y calor.
function recibir(nuevo) {
  const ahora = performance.now();
  const r = nuevo.reloj * 1000;
  const d = ahora - r;
  desfase = !est || d < desfase ? d : desfase + 0.02 * (d - desfase);   // la red solo suma retraso
  const reinicio = !est || nuevo.t < est.t || nuevo.escenario !== est.escenario
    || nuevo.modo !== est.modo || nuevo.semilla !== est.semilla;
  const registro = { r, agentes: nuevo.agentes, porId: new Map(nuevo.agentes.map((f) => [f[0], f])) };

  if (reinicio) {
    estados = [registro];
    fundidoInicio = ahora;
    rutas = new Map();
    rutasV = -1;
    intervalos = [];
    tardanzas = [];
  } else if (nuevo.t !== est.t) {
    const previo = estados[estados.length - 1];
    if (r - previo.r > 320) {
      previo.r = r - 100;                      // tras pausa o paso: anima 100 ms, sin salto
    } else {
      intervalos.push(r - previo.r);
      tardanzas.push(d - desfase);
      if (intervalos.length > 12) { intervalos.shift(); tardanzas.shift(); }
      retraso = limitar(Math.max(...intervalos) + Math.max(...tardanzas) + 10, 70, 350);
    }
    estados.push(registro);
    if (estados.length > 6) estados.shift();
  }

  if (capas.rutas && nuevo.rutas) { rutas = new Map(nuevo.rutas); rutasV = nuevo.rutas_v; }

  const segundo = Math.floor(nuevo.t);
  const muestra = reinicio || segundo !== calorSeg;
  if (muestra && !reinicio) { mezclarCalor(ahora); copiarCalor(calor); }
  est = nuevo;
  if (muestra) {
    calorSeg = segundo;
    pintarCalor();
    if (reinicio) { copiarCalor(calorB); calorInicio = calorFin = 0; }
    else { calorInicio = ahora; calorFin = ahora + Math.max(200, 1000 / nuevo.velocidad); }
    mezcla = -1;
  }
  pendiente = true;
  actualizarPanel();
  pedirCuadro();
}

// ---- Comunicación con Python ----
async function enviar(orden) {
  ordenes++;
  try {
    const r = await fetch('/control', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(orden),
    });
    const datos = await r.json();
    if (!r.ok) throw new Error(datos.error);
    ordenes++;
    recibir(datos);
  } catch (error) {
    mostrarAviso(`No se pudo aplicar la orden: ${error.message}`, true);
  }
}

// Python responde cuando hay un tick nuevo, o con 204 a los 0,5 s si nada cambió.
async function sondear() {
  if (document.hidden) { setTimeout(sondear, 1000); return; }   // pestaña oculta: no consume
  const inicio = performance.now(), marca = ordenes;
  let espera = 500;
  try {
    const r = await fetch(`/estado?desde=${est ? est.seq : ''}${capas.rutas ? `&rutas=1&rv=${rutasV}` : ''}`);
    if (r.status === 200) {
      const datos = await r.json();
      if (marca === ordenes) recibir(datos);
    }
    if (avisoFijo && !est.error) { avisoFijo = false; $('aviso').hidden = true; }
    espera = Math.max(0, SONDEO_MIN_MS - (performance.now() - inicio));
  } catch (error) {
    mostrarAviso('Sin conexión con el servidor. Comprueba que siga ejecutándose en la terminal.', true, 0);
  }
  setTimeout(sondear, espera);
}

function capturar() {
  fundidoInicio = -Infinity;
  dibujar(Infinity);
  lienzo.toBlob((datos) => {
    const enlace = document.createElement('a');
    enlace.href = URL.createObjectURL(datos);
    enlace.download = `multitudes_${est.escenario}_modo${est.modo}_semilla${est.semilla}_t${est.t.toFixed(1)}s.png`;
    enlace.click();
    setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
    mostrarAviso('Captura descargada');
  }, 'image/png');
}

function alternarCapa(nombre, boton) {
  capas[nombre] = !capas[nombre];
  boton.setAttribute('aria-pressed', capas[nombre]);
  if (nombre === 'rutas') {
    rutas = new Map();
    rutasV = -1;
    if (capas.rutas) fetch('/estado?rutas=1&rv=-1').catch(() => {});   // avisa sin esperar al sondeo
  }
  pendiente = true;
  pedirCuadro();
}

// ---- Controles ----
$('btn-iniciar').onclick = () => enviar({ accion: est.fase === 'corriendo' ? 'pausar' : 'iniciar' });
$('btn-paso').onclick = () => enviar({ accion: 'paso' });
$('btn-reiniciar').onclick = () => enviar({ accion: 'reiniciar' });
$('res-reiniciar').onclick = () => enviar({ accion: 'reiniciar' });
$('res-ver').onclick = () => { resumenOculto = true; $('resumen').hidden = true; };
$('capa-calor').onclick = (e) => alternarCapa('calor', e.currentTarget);
$('capa-grupos').onclick = (e) => alternarCapa('grupos', e.currentTarget);
$('capa-rutas').onclick = (e) => alternarCapa('rutas', e.currentTarget);
$('btn-captura').onclick = capturar;
$('tema').onclick = cambiarTema;
$('atajos').onclick = alternarAtajos;

// Pulsar la opción ya elegida no hace nada, para no reiniciar el episodio por error.
for (const b of document.querySelectorAll('[data-modo]')) {
  b.onclick = () => { if (b.dataset.modo !== est.modo) enviar({ accion: 'configurar', modo: b.dataset.modo }); };
}
for (const b of document.querySelectorAll('[data-escenario]')) {
  b.onclick = () => { if (b.dataset.escenario !== est.escenario) enviar({ accion: 'configurar', escenario: b.dataset.escenario }); };
}
for (const b of document.querySelectorAll('[data-semilla]')) {
  b.onclick = () => {
    const semilla = Number(b.dataset.semilla);
    if (semilla !== est.semilla) enviar({ accion: 'configurar', semilla });
  };
}
for (const b of document.querySelectorAll('[data-velocidad]')) {
  b.onclick = () => enviar({ accion: 'velocidad', valor: Number(b.dataset.velocidad) });
}
// Tras un clic con ratón se quita el foco, para que Espacio no repita ese botón.
document.addEventListener('click', (e) => {
  if (e.detail > 0) e.target.closest('button')?.blur();
});

// ---- Atajos de teclado: pulsan el mismo botón, así respetan su estado deshabilitado ----
const ATAJOS = {
  ' ': 'btn-iniciar', arrowright: 'btn-paso', x: 'btn-reiniciar',
  h: 'capa-calor', c: 'capa-grupos', r: 'capa-rutas', s: 'btn-captura', t: 'tema', '?': 'atajos',
  a: '[data-modo="A"]', b: '[data-modo="B"]', p: '[data-modo="B_PSO"]',
  1: '[data-escenario="S1"]', 2: '[data-escenario="S2"]', 3: '[data-escenario="S3"]',
  q: '[data-semilla="42"]', w: '[data-semilla="43"]', e: '[data-semilla="44"]',
};

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey || !est) return;
  const tecla = e.key.toLowerCase();
  if (tecla === 'v') {
    e.preventDefault();
    if (!e.repeat) enviar({ accion: 'velocidad', valor: { 1: 2, 2: 4, 4: 1 }[est.velocidad] });
    return;
  }
  const destino = ATAJOS[tecla];
  if (!destino) return;
  e.preventDefault();
  if (e.repeat && tecla !== 'arrowright') return;
  (document.getElementById(destino) || document.querySelector(destino)).click();
});
document.addEventListener('keyup', (e) => { if (e.key === ' ') e.preventDefault(); });

async function iniciar() {
  leerTema();
  $('tema').setAttribute('aria-checked', document.documentElement.dataset.tema === 'claro');
  $('atajos').setAttribute('aria-checked', document.documentElement.dataset.atajos === 'si');
  cfg = await (await fetch('/config')).json();
  for (const c of [calor, calorA, calorB]) {
    c.width = Math.ceil(cfg.ancho / 2);
    c.height = Math.ceil(cfg.alto / 2);
  }
  ajustarLienzo();
  vigilarEscala();
  sondear();
}
iniciar();
