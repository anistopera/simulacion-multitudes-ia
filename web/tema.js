// Corre en <head>, antes del primer pintado, para que tema y atajos no parpadeen.
try {
  if (localStorage.getItem('tema') === 'claro') document.documentElement.dataset.tema = 'claro';
  if (localStorage.getItem('atajos') === 'si') document.documentElement.dataset.atajos = 'si';
} catch (e) { /* sin almacenamiento: tema oscuro y atajos ocultos */ }
