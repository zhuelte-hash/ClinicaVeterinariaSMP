'use strict';

(() => {
  const app = document.querySelector('#app');
  if (!app) return;

  const enhance = () => {
    const stats = app.querySelector('#content .stats');
    if (!stats || app.querySelector('.pro-dashboard')) return;

    stats.insertAdjacentHTML('afterend', `
      <section class="pro-dashboard">
        <article class="chart-card chart-main">
          <div class="chart-heading"><div><span class="eyebrow">Rendimiento clinico</span><h2>Actividad de la semana</h2></div><span class="chart-filter">Ultimos 7 dias <b>⌄</b></span></div>
          <div class="chart-summary"><strong>24</strong><span><i>+18.4%</i> frente a la semana anterior</span></div>
          <div class="bar-chart" aria-label="Grafico de actividad semanal">
            <div class="bar-col"><span style="height:42%"></span><small>Lun</small></div><div class="bar-col"><span style="height:67%"></span><small>Mar</small></div><div class="bar-col"><span style="height:54%"></span><small>Mié</small></div><div class="bar-col"><span style="height:82%"></span><small>Jue</small></div><div class="bar-col"><span style="height:61%"></span><small>Vie</small></div><div class="bar-col"><span style="height:92%"></span><small>Sáb</small></div><div class="bar-col"><span style="height:38%"></span><small>Dom</small></div>
          </div>
        </article>
        <article class="chart-card chart-donut-card">
          <div class="chart-heading"><div><span class="eyebrow">Estado actual</span><h2>Resumen de citas</h2></div><span class="mini-menu">•••</span></div>
          <div class="donut-wrap"><div class="donut"><strong>18</strong><small>citas</small></div><div class="legend"><span><b class="dot teal"></b>Confirmadas <strong>10</strong></span><span><b class="dot violet"></b>Pendientes <strong>5</strong></span><span><b class="dot gold"></b>Atendidas <strong>3</strong></span></div></div>
        </article>
      </section>
      <section class="pro-widgets">
        <article class="widget-card"><div class="widget-head"><div><span class="eyebrow">Seguimiento</span><h2>Proximas citas</h2></div><span class="widget-icon">⌁</span></div><div class="widget-line"><span class="avatar teal-avatar">L</span><div><strong>Luna</strong><small>Consulta general · Hoy, 09:00</small></div><b class="status-pill">En espera</b></div><div class="widget-line"><span class="avatar violet-avatar">M</span><div><strong>Max</strong><small>Control preventivo · Hoy, 09:30</small></div><b class="status-pill violet-status">Confirmada</b></div><button class="widget-link" data-action="navigate" data-id="Citas">Ver agenda completa →</button></article>
        <article class="widget-card"><div class="widget-head"><div><span class="eyebrow">Actividad reciente</span><h2>Resumen operativo</h2></div><span class="widget-icon gold-icon">★</span></div><div class="progress-row"><div><span>Consultas</span><b>72%</b></div><div class="progress"><i style="width:72%"></i></div></div><div class="progress-row"><div><span>Preventivos</span><b>48%</b></div><div class="progress purple-progress"><i style="width:48%"></i></div></div><div class="progress-row"><div><span>Servicios clinicos</span><b>36%</b></div><div class="progress gold-progress"><i style="width:36%"></i></div></div></article>
      </section>`);
  };

  new MutationObserver(enhance).observe(app, { childList: true, subtree: true });
  enhance();
})();
