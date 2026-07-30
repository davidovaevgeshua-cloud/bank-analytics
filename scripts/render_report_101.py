<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Прибыль банковского сектора РФ — сравнение по годам (2024-2026)</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#0f1420; --panel:#161d2e; --panel2:#1c2438; --border:#2a3450;
    --text:#e7ebf3; --muted:#8a92a8; --pos:#3ddc84; --neg:#ff5c6a;
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--text);font-family:'Segoe UI',Arial,sans-serif;line-height:1.5;}
  .wrap{max-width:1140px;margin:0 auto;padding:32px 20px 60px;}
  h1{font-size:22px;font-weight:600;margin:0 0 4px;}
  .subtitle{color:var(--muted);font-size:14px;margin-bottom:24px;}
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:26px;}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px 18px;}
  .card .label{font-size:12px;color:var(--muted);margin-bottom:8px;}
  .card .value{font-size:20px;font-weight:600;}
  .card .yoy{font-size:12.5px;margin-top:4px;}
  .pos{color:var(--pos);} .neg{color:var(--neg);}
  section{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:20px 22px;margin-bottom:22px;}
  h2{font-size:16px;font-weight:600;margin:0 0 14px;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--border);}
  th{color:var(--muted);font-weight:500;font-size:12px;}
  td.num, th.num{text-align:right;font-variant-numeric:tabular-nums;}
  tr:hover td{background:var(--panel2);}
  .note{font-size:13px;color:var(--muted);}
  .flag{background:#2a2116;border:1px solid #4a3a1f;color:#e8c77a;border-radius:8px;padding:14px 16px;font-size:13.5px;margin-bottom:22px;}
  .flag b{color:#f4d998;}
  canvas{max-height:380px;}
  select{background:var(--panel2);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:14px;width:100%;max-width:420px;}
  .selector-row{display:flex;align-items:center;gap:14px;margin-bottom:18px;flex-wrap:wrap;}
  .selector-row .selstats{font-size:13px;color:var(--muted);}
  .selector-row .selstats b{font-size:14.5px;}
</style>
</head>
<body>
<div class="wrap">

  <h1>Прибыль банковского сектора РФ — сравнение по годам</h1>
  <div class="subtitle">Данные Банка России, форма 101. Охват: январь 2024 г. — май 2026 г.</div>

  <div class="flag">
    <b>Методология.</b> Финансовый результат — по счёту 706 «Финансовый результат текущего года» (обнуляется 1 января). Прибыль за январь каждого года — накопленный итог самого января, за остальные месяцы — разница накопленных итогов текущего и предыдущего месяца. 2026 год представлен по имеющимся месяцам (январь–май), 2024 и 2025 — целиком.
  </div>

  <div class="cards">
    <div class="card">
      <div class="label">Май 2026 к маю 2025</div>
      <div class="value" id="cardMay"></div>
      <div class="yoy" id="cardMayYoy"></div>
    </div>
    <div class="card">
      <div class="label">YTD янв–май 2026 к янв–май 2025</div>
      <div class="value" id="cardYtd"></div>
      <div class="yoy" id="cardYtdYoy"></div>
    </div>
    <div class="card">
      <div class="label">Весь 2025 г. к 2024 г.</div>
      <div class="value" id="cardFy25"></div>
      <div class="yoy" id="cardFy25Yoy"></div>
    </div>
    <div class="card">
      <div class="label">Весь 2024 г.</div>
      <div class="value" id="cardFy24"></div>
      <div class="yoy">итог года целиком</div>
    </div>
  </div>

  <section>
    <h2>Прибыль сектора по месяцам — сравнение 2024/2025/2026, млрд ₽</h2>
    <canvas id="sectorMonthlyYoy"></canvas>
  </section>

  <section>
    <h2>Помесячные значения и динамика г/г</h2>
    <table>
      <thead><tr><th>Месяц</th><th class="num">2024</th><th class="num">2025</th><th class="num">2026</th><th class="num">г/г, 2025</th><th class="num">г/г, 2026</th></tr></thead>
      <tbody id="sectorTable"></tbody>
    </table>
  </section>

  <section>
    <h2>Накопленная прибыль сектора с начала года (YTD), млрд ₽</h2>
    <canvas id="sectorYtdYoy"></canvas>
  </section>

  <section>
    <h2>Динамика по выбранному банку — сравнение по годам</h2>
    <div class="selector-row">
      <select id="bankSelect"></select>
      <div class="selstats" id="bankStats"></div>
    </div>
    <canvas id="bankMonthlyChart"></canvas>
    <div style="height:22px"></div>
    <canvas id="bankYtdChart"></canvas>
  </section>

  <section>
    <h2>Помесячные значения по выбранному банку, млрд ₽</h2>
    <table>
      <thead><tr><th>Месяц</th><th class="num">2024</th><th class="num">2025</th><th class="num">2026</th><th class="num">г/г, 2025</th><th class="num">г/г, 2026</th></tr></thead>
      <tbody id="bankTable"></tbody>
    </table>
  </section>

</div>

<script>
const DATA = {"month_names": ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"], "sector": {"monthly_2024": [331.5, 234.4, 271.1, 274.3, 273.8, 344.8, 331.8, 431.7, 354.5, 357.7, 479.0, 206.1], "monthly_2025": [268.7, 246.5, 234.9, 295.2, 292.4, 455.9, 347.6, 309.6, 373.4, 307.8, 444.3, 183.4], "monthly_2026": [385.1, 360.8, 419.2, 339.3, 352.3], "ytd_2024": [331.5, 565.9, 837.0, 1111.3, 1385.1, 1729.9, 2061.7, 2493.4, 2847.9, 3205.6, 3684.6, 3890.7], "ytd_2025": [268.7, 515.2, 750.1, 1045.3, 1337.7, 1793.6, 2141.2, 2450.8, 2824.2, 3132.0, 3576.3, 3759.7], "ytd_2026": [385.1, 745.9, 1165.1, 1504.4, 1856.7]}, "banks": {"1481": {"name": "СБЕРБАНК РОССИИ", "monthly_2024": [115.126, 120.398, 128.461, 131.065, 133.359, 140.332, 141.162, 142.744, 140.571, 134.233, 117.327, 117.604], "monthly_2025": [132.947, 134.391, 137.186, 137.795, 140.575, 143.689, 144.919, 148.078, 150.275, 149.619, 148.743, 125.938], "monthly_2026": [161.749, 162.802, 166.44, 166.832, 169.374], "ytd_2024": [115.126, 235.524, 363.985, 495.05, 628.409, 768.741, 909.903, 1052.647, 1193.218, 1327.451, 1444.778, 1562.382], "ytd_2025": [132.947, 267.338, 404.524, 542.319, 682.894, 826.583, 971.502, 1119.58, 1269.855, 1419.474, 1568.217, 1694.155], "ytd_2026": [161.749, 324.551, 490.991, 657.823, 827.197]}, "1000": {"name": "ВТБ", "monthly_2024": [22.238, 8.563, 4.41, 8.343, 15.763, 76.327, 11.651, 38.433, 25.306, 104.115, 129.8, 165.02], "monthly_2025": [5.11, 34.5, 6.121, 27.477, 6.575, 84.928, 20.702, 25.205, 41.723, 13.113, 77.524, 22.844], "monthly_2026": [27.414, 53.674, 59.395, 34.111, 33.094], "ytd_2024": [22.238, 30.801, 35.211, 43.554, 59.317, 135.644, 147.295, 185.728, 211.034, 315.149, 444.949, 609.969], "ytd_2025": [5.11, 39.61, 45.731, 73.208, 79.783, 164.711, 185.413, 210.618, 252.341, 265.454, 342.978, 365.822], "ytd_2026": [27.414, 81.088, 140.483, 174.594, 207.688]}, "1326": {"name": "АЛЬФА-БАНК", "monthly_2024": [3.32, 2.491, 2.678, 20.679, 17.154, 24.812, 29.169, 58.111, 31.491, 2.58, 10.911, -3.791], "monthly_2025": [24.129, -7.875, 12.892, 28.311, 25.71, 55.005, 25.617, 12.11, 21.052, 24.709, 27.001, 32.932], "monthly_2026": [38.206, 23.63, 29.6, 20.148, 25.095], "ytd_2024": [3.32, 5.811, 8.489, 29.168, 46.322, 71.134, 100.303, 158.414, 189.905, 192.485, 203.396, 199.605], "ytd_2025": [24.129, 16.254, 29.146, 57.457, 83.167, 138.172, 163.789, 175.899, 196.951, 221.66, 248.661, 281.593], "ytd_2026": [38.206, 61.836, 91.436, 111.584, 136.679]}, "354": {"name": "ГАЗПРОМБАНК", "monthly_2024": [18.987, 12.755, 13.947, 11.287, 30.139, 16.335, 15.26, 47.247, 25.595, 13.275, 47.118, -42.462], "monthly_2025": [-3.823, -0.733, 6.926, 5.068, 33.71, 18.101, 13.215, 34.177, 22.436, 12.756, 16.9, -10.033], "monthly_2026": [18.338, 14.11, 26.091, 9.225, 26.109], "ytd_2024": [18.987, 31.742, 45.689, 56.976, 87.115, 103.45, 118.71, 165.957, 191.552, 204.827, 251.945, 209.483], "ytd_2025": [-3.823, -4.556, 2.37, 7.438, 41.148, 59.249, 72.464, 106.641, 129.077, 141.833, 158.733, 148.7], "ytd_2026": [18.338, 32.448, 58.539, 67.764, 93.873]}, "2673": {"name": "ТБанк", "monthly_2024": [5.111, 5.448, 6.781, 8.274, 1.943, 1.313, 4.372, 5.276, 4.109, 7.852, 7.285, 2.955], "monthly_2025": [0.861, 1.643, 3.923, 2.315, 0.171, 3.857, 12.776, 7.722, 14.851, 19.496, 20.289, 24.242], "monthly_2026": [19.352, 13.766, 17.276, 7.309, 15.859], "ytd_2024": [5.111, 10.559, 17.34, 25.614, 27.557, 28.87, 33.242, 38.518, 42.627, 50.479, 57.764, 60.719], "ytd_2025": [0.861, 2.504, 6.427, 8.742, 8.913, 12.77, 25.546, 33.268, 48.119, 67.615, 87.904, 112.146], "ytd_2026": [19.352, 33.118, 50.394, 57.703, 73.562]}, "841": {"name": "ВАЙЛДБЕРРИЗ БАНК", "monthly_2024": [0.099, 0.17, 0.438, 1.162, 1.499, 1.413, 2.174, 2.363, 2.156, 2.845, 2.629, 4.862], "monthly_2025": [4.801, 2.337, 3.875, 3.146, 4.986, 5.529, 4.951, 5.494, 7.001, 6.966, 6.894, 7.985], "monthly_2026": [9.297, 9.646, 15.614, 13.001, 11.592], "ytd_2024": [0.099, 0.269, 0.707, 1.869, 3.368, 4.781, 6.955, 9.318, 11.474, 14.319, 16.948, 21.81], "ytd_2025": [4.801, 7.138, 11.013, 14.159, 19.145, 24.674, 29.625, 35.119, 42.12, 49.086, 55.98, 63.965], "ytd_2026": [9.297, 18.943, 34.557, 47.558, 59.15]}, "963": {"name": "СОВКОМБАНК", "monthly_2024": [3.105, 3.334, 5.003, 1.986, 0.046, 14.365, -2.141, 5.391, 4.479, -4.206, 6.654, 4.808], "monthly_2025": [-3.462, -8.682, -4.203, 8.974, 7.603, 3.714, 2.789, 1.995, 14.262, -4.027, 11.659, 13.467], "monthly_2026": [2.604, 3.406, 9.888, 23.412, 10.226], "ytd_2024": [3.105, 6.439, 11.442, 13.428, 13.474, 27.839, 25.698, 31.089, 35.568, 31.362, 38.016, 42.824], "ytd_2025": [-3.462, -12.144, -16.347, -7.373, 0.23, 3.944, 6.733, 8.728, 22.99, 18.963, 30.622, 44.089], "ytd_2026": [2.604, 6.01, 15.898, 39.31, 49.536]}, "2312": {"name": "БАНК ДОМ.РФ", "monthly_2024": [6.929, 4.565, 1.298, 1.437, -0.213, 3.261, 4.672, 10.383, 5.095, 3.998, 6.601, -2.211], "monthly_2025": [4.526, 4.024, 1.196, 7.674, 2.842, 10.698, 5.663, 6.671, 7.726, 5.429, 11.149, 12.687], "monthly_2026": [11.358, 10.091, 9.784, 0.843, 12.214], "ytd_2024": [6.929, 11.494, 12.792, 14.229, 14.016, 17.277, 21.949, 32.332, 37.427, 41.425, 48.026, 45.815], "ytd_2025": [4.526, 8.55, 9.746, 17.42, 20.262, 30.96, 36.623, 43.294, 51.02, 56.449, 67.598, 80.285], "ytd_2026": [11.358, 21.449, 31.233, 32.076, 44.29]}, "3292": {"name": "РАЙФФАЙЗЕНБАНК", "monthly_2024": [13.717, 9.925, 8.844, 11.864, 11.326, 15.576, 9.064, 11.525, 15.448, 13.359, 10.967, 10.873], "monthly_2025": [11.88, 8.763, -19.061, 11.212, 8.35, 62.799, 9.213, 9.278, 8.613, 7.867, 31.727, -75.405], "monthly_2026": [7.121, 7.195, 7.458, 7.694, 6.845], "ytd_2024": [13.717, 23.642, 32.486, 44.35, 55.676, 71.252, 80.316, 91.841, 107.289, 120.648, 131.615, 142.488], "ytd_2025": [11.88, 20.643, 1.582, 12.794, 21.144, 83.943, 93.156, 102.434, 111.047, 118.914, 150.641, 75.236], "ytd_2026": [7.121, 14.316, 21.774, 29.468, 36.313]}, "3349": {"name": "РОССЕЛЬХОЗБАНК", "monthly_2024": [37.618, 6.978, 6.057, 6.96, -7.91, 3.882, 6.321, -1.799, 6.754, 3.079, 5.808, -24.102], "monthly_2025": [-3.091, 15.409, 10.693, 2.054, 5.816, 1.297, 16.621, 5.238, -4.107, 7.05, 12.17, -13.784], "monthly_2026": [11.687, 4.19, 9.244, 5.94, 1.846], "ytd_2024": [37.618, 44.596, 50.653, 57.613, 49.703, 53.585, 59.906, 58.107, 64.861, 67.94, 73.748, 49.646], "ytd_2025": [-3.091, 12.318, 23.011, 25.065, 30.881, 32.178, 48.799, 54.037, 49.93, 56.98, 69.15, 55.366], "ytd_2026": [11.687, 15.877, 25.121, 31.061, 32.907]}, "1978": {"name": "МОСКОВСКИЙ КРЕДИТНЫЙ БАНК", "monthly_2024": [7.528, 2.513, 3.225, 5.063, 1.755, 1.399, 2.708, 3.269, 1.157, 2.715, 4.59, -4.072], "monthly_2025": [7.772, 0.243, -2.67, 10.292, 1.833, -0.289, 4.816, 4.489, 3.627, -1.228, 0.397, -8.216], "monthly_2026": [5.066, 5.964, 1.967, 0.853, 0.998], "ytd_2024": [7.528, 10.041, 13.266, 18.329, 20.084, 21.483, 24.191, 27.46, 28.617, 31.332, 35.922, 31.85], "ytd_2025": [7.772, 8.015, 5.345, 15.637, 17.47, 17.181, 21.997, 26.486, 30.113, 28.885, 29.282, 21.066], "ytd_2026": [5.066, 11.03, 12.997, 13.85, 14.848]}, "3027": {"name": "ЯНДЕКС БАНК", "monthly_2024": [0.048, -0.291, -0.497, -0.304, -0.25, -0.652, -0.555, 0.295, 0.288, 0.292, 0.041, -1.402], "monthly_2025": [0.421, -0.053, 0.281, 0.338, 2.199, 0.892, 1.048, -0.459, 1.569, -1.483, 0.815, 1.088], "monthly_2026": [1.381, 0.924, 1.339, 0.64, 1.762], "ytd_2024": [0.048, -0.243, -0.74, -1.044, -1.294, -1.946, -2.501, -2.206, -1.918, -1.626, -1.585, -2.987], "ytd_2025": [0.421, 0.368, 0.649, 0.987, 3.186, 4.078, 5.126, 4.667, 6.236, 4.753, 5.568, 6.656], "ytd_2026": [1.381, 2.305, 3.644, 4.284, 6.046]}, "3542": {"name": "ОЗОН БАНК", "monthly_2024": [0.959, 1.235, 0.836, 0.599, 1.246, 1.341, -0.354, 1.781, 1.542, 1.2, 2.604, 2.333], "monthly_2025": [2.509, 2.448, 2.359, 1.186, 2.067, 2.906, 1.515, 3.078, 3.44, 1.097, 2.57, 2.905], "monthly_2026": [3.532, 2.375, 2.946, 1.9, 3.197], "ytd_2024": [0.959, 2.194, 3.03, 3.629, 4.875, 6.216, 5.862, 7.643, 9.185, 10.385, 12.989, 15.322], "ytd_2025": [2.509, 4.957, 7.316, 8.502, 10.569, 13.475, 14.99, 18.068, 21.508, 22.605, 25.175, 28.08], "ytd_2026": [3.532, 5.907, 8.853, 10.753, 13.95]}}, "bank_order": [1481, 1000, 1326, 354, 2673, 841, 963, 2312, 3292, 3349, 1978, 3027, 3542]};

function fmt(x){
  if(x===null || x===undefined) return '—';
  return x.toLocaleString('ru-RU',{minimumFractionDigits:1,maximumFractionDigits:1});
}
function pctStr(cur, prev){
  if(cur===null||cur===undefined||prev===null||prev===undefined||prev===0) return '—';
  const p = (cur/prev-1)*100;
  const sign = p>=0?'+':'';
  return sign + p.toFixed(1) + '%';
}
function pctClass(cur, prev){
  if(cur===null||cur===undefined||prev===null||prev===undefined) return '';
  return (cur-prev)>=0 ? 'pos':'neg';
}

const commonOpts = {
  scales: {
    x: { ticks:{color:'#8a92a8'}, grid:{display:false} },
    y: { ticks:{color:'#8a92a8'}, grid:{color:'#2a3450'} }
  },
  plugins: { legend: { labels:{color:'#e7ebf3'} } }
};

function pad12(arr){ return arr.concat(new Array(12-arr.length).fill(null)); }

// ---- cards ----
const s = DATA.sector;
document.getElementById('cardMay').textContent = fmt(s.monthly_2026[4]) + ' млрд ₽';
document.getElementById('cardMay').className = 'value ' + pctClass(s.monthly_2026[4], s.monthly_2025[4]);
document.getElementById('cardMayYoy').textContent = pctStr(s.monthly_2026[4], s.monthly_2025[4]) + ' г/г (' + fmt(s.monthly_2025[4]) + ' млрд ₽ в мае 2025 г.)';
document.getElementById('cardMayYoy').className = 'yoy ' + pctClass(s.monthly_2026[4], s.monthly_2025[4]);

document.getElementById('cardYtd').textContent = fmt(s.ytd_2026[4]) + ' млрд ₽';
document.getElementById('cardYtd').className = 'value ' + pctClass(s.ytd_2026[4], s.ytd_2025[4]);
document.getElementById('cardYtdYoy').textContent = pctStr(s.ytd_2026[4], s.ytd_2025[4]) + ' г/г (' + fmt(s.ytd_2025[4]) + ' млрд ₽ за янв–май 2025 г.)';
document.getElementById('cardYtdYoy').className = 'yoy ' + pctClass(s.ytd_2026[4], s.ytd_2025[4]);

document.getElementById('cardFy25').textContent = fmt(s.ytd_2025[11]) + ' млрд ₽';
document.getElementById('cardFy25').className = 'value ' + pctClass(s.ytd_2025[11], s.ytd_2024[11]);
document.getElementById('cardFy25Yoy').textContent = pctStr(s.ytd_2025[11], s.ytd_2024[11]) + ' г/г (' + fmt(s.ytd_2024[11]) + ' млрд ₽ за 2024 г.)';
document.getElementById('cardFy25Yoy').className = 'yoy ' + pctClass(s.ytd_2025[11], s.ytd_2024[11]);

document.getElementById('cardFy24').textContent = fmt(s.ytd_2024[11]) + ' млрд ₽';

// ---- Sector monthly grouped bars ----
new Chart(document.getElementById('sectorMonthlyYoy'), {
  type:'bar',
  data:{
    labels: DATA.month_names,
    datasets:[
      {label:'2024', data: s.monthly_2024, backgroundColor:'#8a92a8', borderRadius:4},
      {label:'2025', data: s.monthly_2025, backgroundColor:'#4f8cff', borderRadius:4},
      {label:'2026', data: pad12(s.monthly_2026), backgroundColor:'#3ddc84', borderRadius:4},
    ]
  },
  options: commonOpts
});

// sector table
const sTbody = document.getElementById('sectorTable');
DATA.month_names.forEach((mn,i)=>{
  const v24 = s.monthly_2024[i];
  const v25 = s.monthly_2025[i];
  const v26 = i<5 ? s.monthly_2026[i] : null;
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${mn}</td>
    <td class="num">${fmt(v24)}</td>
    <td class="num">${fmt(v25)}</td>
    <td class="num">${fmt(v26)}</td>
    <td class="num ${pctClass(v25,v24)}">${pctStr(v25,v24)}</td>
    <td class="num ${pctClass(v26,v25)}">${pctStr(v26,v25)}</td>`;
  sTbody.appendChild(tr);
});

// ---- Sector YTD line comparison ----
new Chart(document.getElementById('sectorYtdYoy'), {
  type:'line',
  data:{
    labels: DATA.month_names,
    datasets:[
      {label:'2024, накоплено с начала года', data: s.ytd_2024, borderColor:'#8a92a8', backgroundColor:'rgba(138,146,168,0.10)', fill:true, tension:0.25, pointRadius:2, spanGaps:false},
      {label:'2025, накоплено с начала года', data: s.ytd_2025, borderColor:'#4f8cff', backgroundColor:'rgba(79,140,255,0.12)', fill:true, tension:0.25, pointRadius:3, spanGaps:false},
      {label:'2026, накоплено с начала года', data: pad12(s.ytd_2026), borderColor:'#3ddc84', backgroundColor:'rgba(61,220,132,0.15)', fill:true, tension:0.25, pointRadius:3, spanGaps:false},
    ]
  },
  options: commonOpts
});

// ---- Bank selector ----
const select = document.getElementById('bankSelect');
DATA.bank_order.forEach(regn=>{
  const b = DATA.banks[regn];
  const opt = document.createElement('option');
  opt.value = regn;
  opt.textContent = b.name;
  select.appendChild(opt);
});

let bankMonthlyChart=null, bankYtdChart=null;
function renderBank(regn){
  const b = DATA.banks[regn];
  if(!b) return;

  document.getElementById('bankStats').innerHTML =
    `Май 2026: <b class="${pctClass(b.monthly_2026[4], b.monthly_2025[4])}">${fmt(b.monthly_2026[4])}</b> млрд ₽ (г/г ${pctStr(b.monthly_2026[4], b.monthly_2025[4])}) &nbsp;|&nbsp; ` +
    `YTD янв–май: <b class="${pctClass(b.ytd_2026[4], b.ytd_2025[4])}">${fmt(b.ytd_2026[4])}</b> млрд ₽ (г/г ${pctStr(b.ytd_2026[4], b.ytd_2025[4])}) &nbsp;|&nbsp; ` +
    `2025 г. целиком: <b>${fmt(b.ytd_2025[11])}</b> млрд ₽ (г/г к 2024 г.: ${pctStr(b.ytd_2025[11], b.ytd_2024[11])})`;

  if(bankMonthlyChart) bankMonthlyChart.destroy();
  bankMonthlyChart = new Chart(document.getElementById('bankMonthlyChart'), {
    type:'bar',
    data:{
      labels: DATA.month_names,
      datasets:[
        {label:'2024', data: b.monthly_2024, backgroundColor:'#8a92a8', borderRadius:4},
        {label:'2025', data: b.monthly_2025, backgroundColor:'#4f8cff', borderRadius:4},
        {label:'2026', data: pad12(b.monthly_2026), backgroundColor:'#3ddc84', borderRadius:4},
      ]
    },
    options: Object.assign({}, commonOpts, {plugins:{legend:{labels:{color:'#e7ebf3'}}, title:{display:true, text:'Прибыль за месяц, млрд ₽', color:'#8a92a8', font:{size:12}}}})
  });

  if(bankYtdChart) bankYtdChart.destroy();
  bankYtdChart = new Chart(document.getElementById('bankYtdChart'), {
    type:'line',
    data:{
      labels: DATA.month_names,
      datasets:[
        {label:'2024, накоплено с начала года', data: b.ytd_2024, borderColor:'#8a92a8', backgroundColor:'rgba(138,146,168,0.10)', fill:true, tension:0.25, pointRadius:2, spanGaps:false},
        {label:'2025, накоплено с начала года', data: b.ytd_2025, borderColor:'#4f8cff', backgroundColor:'rgba(79,140,255,0.12)', fill:true, tension:0.25, pointRadius:3, spanGaps:false},
        {label:'2026, накоплено с начала года', data: pad12(b.ytd_2026), borderColor:'#3ddc84', backgroundColor:'rgba(61,220,132,0.15)', fill:true, tension:0.25, pointRadius:3, spanGaps:false},
      ]
    },
    options: Object.assign({}, commonOpts, {plugins:{legend:{labels:{color:'#e7ebf3'}}, title:{display:true, text:'Накопленная прибыль (YTD), млрд ₽', color:'#8a92a8', font:{size:12}}}})
  });

  const tbody = document.getElementById('bankTable');
  tbody.innerHTML='';
  DATA.month_names.forEach((mn,i)=>{
    const v24 = b.monthly_2024[i];
    const v25 = b.monthly_2025[i];
    const v26 = i<5 ? b.monthly_2026[i] : null;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${mn}</td>
      <td class="num">${fmt(v24)}</td>
      <td class="num">${fmt(v25)}</td>
      <td class="num">${fmt(v26)}</td>
      <td class="num ${pctClass(v25,v24)}">${pctStr(v25,v24)}</td>
      <td class="num ${pctClass(v26,v25)}">${pctStr(v26,v25)}</td>`;
    tbody.appendChild(tr);
  });
}

select.addEventListener('change', e=>renderBank(e.target.value));
renderBank(String(DATA.bank_order[0]));
</script>
</body>
</html>
