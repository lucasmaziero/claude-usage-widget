/* Agent Gauge - landing page behaviour.
 *
 * Three jobs, in order of how much they matter:
 *
 *   1. the running widget in the hero, which is the page's whole argument
 *   2. the download cards, filled from the GitHub API so the page cannot go
 *      stale the way a hand-written filename does
 *   3. the language switch, one dictionary per language, the same shape the
 *      app's own i18n.py uses
 */
'use strict';

/* ────────────────────────────────────────────────────────────── i18n */
const STRINGS = {
  en: {
    'skip': 'Skip to downloads',

    'hero.title': "Your coding agent's limits, where you can see them.",
    'hero.lede': 'A floating widget that reads what Claude Code or Codex already knows about your quota, and tells you how much of the five-hour window is gone before it stops you.',
    'hero.cta': 'Download',
    'hero.source': 'Read the source',
    'hero.fine': 'Free and MIT licensed. Nothing to configure: it reads the credentials the agent already wrote.',
    'hero.caption': 'Running, not a screenshot. The collection interval is compressed so you can watch a cycle.',

    'how.title': 'The number was always in the response. Nobody was reading it.',
    'how.lede': 'There is no usage endpoint for subscription accounts. Utilization rides along in the headers of any reply, so the widget sends the smallest request that exists — one output token — purely to read them.',
    'how.b1': 'of the five-hour window, on the gauge',
    'how.b2': 'until it resets, counted down every second',
    'how.b3': 'of the weekly window, on the second row',
    'how.b4': 'the status chip, and which window binds first',
    'how.c1t': 'Nothing to configure',
    'how.c1b': 'The token comes from wherever the agent put it — a file, or the login keychain on macOS — and is re-read every cycle. When the agent refreshes it, the widget follows on its own. Nothing is refreshed on your behalf: spending a rotating refresh token could log you out of the agent itself.',
    'how.c2t': 'Real token counts',
    'how.c2b': 'The headers only carry percentages. The absolute numbers exist only in the transcripts on your disk, so those are read straight off it — no second account, no telemetry, nothing leaves the machine.',

    'agents.title': 'Both meter the same two windows.',
    'agents.lede': 'A rolling five hours and a week, at 18000 and 604800 seconds exactly, each a percentage with a reset. That is why one widget wears either without redrawing anything. Pick which in the menu; the panel names the one in view and wears its mark, because the ring and the rows look identical either way.',
    'agents.c1t': 'Claude Code',
    'agents.c1b': 'No usage endpoint exists, so a reading costs the smallest request there is — one output token — sent purely to read the rate-limit headers off the reply. Real token counts come from the transcripts on your disk.',
    'agents.c2t': 'Codex',
    'agents.c2b': 'A usage endpoint exists, so a reading costs nothing against your quota. It belongs to the ChatGPT web backend rather than a published API, so a reply that arrives without the two windows is reported as a failed reading rather than guessed at.',

    'alert.title': 'It speaks first, once.',
    'alert.lede': "A display only works if you look at it. Once per five-hour window, when usage first crosses a threshold you set, the widget says so through your system's own notifications — and it says the part worth acting on: not that you are at 80%, but that at this rate you have forty minutes left.",

    'ui.title': 'A glance, and the whole story.',
    'ui.cap1': 'No number appears twice. The ring says how much of the window is spent, the rows say how long is left. Drag it anywhere; the position is saved.',
    'ui.cap2': 'Click for the panel: the five-hour window on its own card, the weekly one below, real token counts, and how long until you hit the ceiling at the current rate.',

    'dl.title': 'Pick your machine.',
    'dl.lede': 'Every build is unsigned, so each system objects in its own way. The note under each one says how to get past it.',
    'dl.win': 'Installs per user, no admin. SmartScreen warns about an unknown publisher — choose More info, then Run anyway.',
    'dl.silicon': 'Apple Silicon',
    'dl.mac': 'Right-click the app and choose Open the first time. The first poll asks for keychain access, because that is where your token lives.',
    'dl.mac2': 'Same as above. Built separately because there is no universal binary for the Qt runtime this uses.',
    'dl.linux': 'chmod +x and run. GNOME needs an AppIndicator extension for the tray; without one the widget stays on screen instead.',
    'dl.note': 'Requires the agent you want to watch to have been signed in once on the same machine. A SHA-256 is published beside every file.',
    'dl.source': 'or from source',

    'foot.by': 'Built by'
  },

  pt: {
    'skip': 'Ir para os downloads',

    'hero.title': 'Os limites do seu agente, onde dá para ver.',
    'hero.lede': 'Um widget flutuante que lê o que o Claude Code ou o Codex já sabem sobre a sua cota, e diz quanto da janela de cinco horas foi embora antes que ela te pare.',
    'hero.cta': 'Baixar',
    'hero.source': 'Ver o código',
    'hero.fine': 'Gratuito e sob licença MIT. Nada para configurar: ele lê as credenciais que o agente já gravou.',
    'hero.caption': 'Rodando, não é um print. O intervalo de coleta está acelerado para você ver um ciclo inteiro.',

    'how.title': 'O número sempre esteve na resposta. Ninguém estava lendo.',
    'how.lede': 'Não existe endpoint de uso para contas de assinatura. A utilização vem junto nos headers de qualquer resposta, então o widget manda a menor requisição que existe — um token de saída — só para lê-los.',
    'how.b1': 'da janela de cinco horas, no medidor',
    'how.b2': 'até o reset, contando de segundo em segundo',
    'how.b3': 'da janela semanal, na segunda linha',
    'how.b4': 'o chip de status, e qual janela é o gargalo',
    'how.c1t': 'Nada para configurar',
    'how.c1b': 'O token sai de onde o agente o guardou — um arquivo, ou o chaveiro de login no macOS — e é relido a cada ciclo. Quando o agente renova, o widget acompanha sozinho. Nada é renovado por você: gastar um refresh token rotativo poderia te deslogar do próprio agente.',
    'how.c2t': 'Contagem real de tokens',
    'how.c2b': 'Os headers só trazem porcentagem. Os números absolutos existem apenas nos transcripts do seu disco, então são lidos direto de lá — sem segunda conta, sem telemetria, nada sai da máquina.',

    'agents.title': 'Os dois medem as mesmas duas janelas.',
    'agents.lede': 'Cinco horas móveis e uma semana, de 18000 e 604800 segundos exatos, cada uma uma porcentagem com reset. É por isso que um widget só veste qualquer um dos dois sem redesenhar nada. Escolha qual no menu; o painel nomeia o que está à vista e veste a marca dele, porque o anel e as linhas são idênticos nos dois casos.',
    'agents.c1t': 'Claude Code',
    'agents.c1b': 'Não existe endpoint de uso, então a leitura custa a menor requisição possível — um token de saída — enviada só para ler os headers de limite da resposta. A contagem real de tokens vem dos transcripts do seu disco.',
    'agents.c2t': 'Codex',
    'agents.c2b': 'Existe endpoint de uso, então a leitura não custa nada da sua cota. Ele pertence ao backend web do ChatGPT e não a uma API publicada, então uma resposta que chegue sem as duas janelas é reportada como leitura que falhou, não adivinhada.',

    'alert.title': 'Ele fala primeiro, uma vez.',
    'alert.lede': 'Mostrador só funciona se você olhar. Uma vez por janela de cinco horas, quando o uso cruza um limiar que você define, o widget avisa pelas notificações do seu próprio sistema — e diz a parte que dá para agir em cima: não que você está em 80%, mas que nesse ritmo sobram quarenta minutos.',

    'ui.title': 'Uma olhada, e a história inteira.',
    'ui.cap1': 'Nenhum número aparece duas vezes. O anel diz quanto da janela foi gasto, as linhas dizem quanto falta. Arraste para onde quiser; a posição fica salva.',
    'ui.cap2': 'Clique para abrir o painel: a janela de cinco horas no próprio cartão, a semanal abaixo, contagem real de tokens, e quanto falta para bater no teto no ritmo atual.',

    'dl.title': 'Escolha sua máquina.',
    'dl.lede': 'Nenhum build é assinado, então cada sistema reclama do seu jeito. A nota embaixo de cada um diz como passar por isso.',
    'dl.win': 'Instala por usuário, sem admin. O SmartScreen avisa "editor desconhecido" — clique em Mais informações e depois Executar assim mesmo.',
    'dl.silicon': 'Apple Silicon',
    'dl.mac': 'Na primeira vez, clique com o botão direito e escolha Abrir. A primeira coleta pede acesso ao chaveiro, porque é lá que mora seu token.',
    'dl.mac2': 'Igual ao de cima. Vem separado porque não existe binário universal para o runtime Qt que ele usa.',
    'dl.linux': 'chmod +x e execute. O GNOME precisa de uma extensão AppIndicator para a bandeja; sem ela o widget fica na tela no lugar dela.',
    'dl.note': 'Exige ter feito login uma vez na mesma máquina, no agente que você quer monitorar. Um SHA-256 é publicado ao lado de cada arquivo.',
    'dl.source': 'ou pelo código-fonte',

    'foot.by': 'Feito por'
  }
};

const store = {
  get(key) { try { return localStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* private mode */ } }
};

function setLanguage(code) {
  const dict = STRINGS[code] || STRINGS.en;
  document.documentElement.lang = code === 'pt' ? 'pt-BR' : 'en';

  for (const node of document.querySelectorAll('[data-i18n]')) {
    const text = dict[node.dataset.i18n];
    if (text) node.textContent = text;
  }
  for (const button of document.querySelectorAll('.lang button')) {
    button.setAttribute('aria-pressed', String(button.dataset.lang === code));
  }

  // The panel screenshot is rendered per language; an English page showing a
  // Portuguese panel would be the one thing here contradicting itself.
  const panel = document.getElementById('shot-panel');
  if (panel) panel.src = `shot-panel-${code}.png`;

  store.set('lang', code);
}

/* ──────────────────────────────────── the widget, actually running */
const RING_R = 27, ORBIT_R = 33.5;
const RING_C = 2 * Math.PI * RING_R;
const ORBIT_C = 2 * Math.PI * ORBIT_R;

const POLL_SECONDS = 6;     // compressed; the real default is 120
const BUSY_MS = 1100;

/* theme.grad_color: a continuous green -> amber -> red ramp. */
const OK = [74, 222, 128], WARN = [251, 191, 36], BAD = [248, 113, 113];

function mix(a, b, t) {
  t = Math.min(Math.max(t, 0), 1);
  return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(',')})`;
}

function gradColor(pct) {
  pct = Math.min(Math.max(pct, 0), 100);
  return pct <= 50 ? mix(WARN, OK, 1 - pct / 50) : mix(BAD, WARN, 1 - (pct - 50) / 50);
}

/* theme.fmt_countdown, near enough: days and hours, hours and minutes, or
 * minutes alone. Never a unit the reader has to convert in their head. */
function countdown(seconds) {
  seconds = Math.max(0, Math.round(seconds));
  const d = Math.floor(seconds / 86400);
  const h = Math.floor(seconds % 86400 / 3600);
  const m = Math.floor(seconds % 3600 / 60);
  if (d) return `${d}d${String(h).padStart(2, '0')}h`;
  if (h) return `${h}h${String(m).padStart(2, '0')}`;
  return `${m}min`;
}

function clockAt(seconds) {
  const when = new Date(Date.now() + seconds * 1000);
  return `${String(when.getHours()).padStart(2, '0')}:${String(when.getMinutes()).padStart(2, '0')}`;
}

function startWidget() {
  const el = {
    widget: document.getElementById('widget'),
    ring: document.getElementById('ring'),
    orbit: document.getElementById('orbit'),
    pct: document.getElementById('pct'),
    h5Left: document.getElementById('h5-left'),
    h5Clock: document.getElementById('h5-clock'),
    d7: document.getElementById('d7'),
    d7Left: document.getElementById('d7-left')
  };
  if (!el.widget) return;

  const state = { h5: 37, d7: 8, h5Reset: 8040, d7Reset: 169200, poll: POLL_SECONDS, busy: false };

  function draw() {
    el.ring.style.strokeDasharray = RING_C;
    el.ring.style.strokeDashoffset = RING_C * (1 - state.h5 / 100);
    el.ring.style.stroke = gradColor(state.h5);

    el.orbit.style.strokeDasharray = ORBIT_C;
    el.orbit.style.strokeDashoffset = ORBIT_C * (1 - state.poll / POLL_SECONDS);

    el.pct.textContent = Math.round(state.h5);
    el.h5Left.textContent = countdown(state.h5Reset);
    el.h5Clock.textContent = clockAt(state.h5Reset);
    el.d7.textContent = `${Math.round(state.d7)}%`;
    el.d7Left.textContent = countdown(state.d7Reset);
    el.widget.setAttribute('aria-label',
      `Floating widget: ${Math.round(state.h5)} percent of the five-hour window used`);
  }

  draw();
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  setInterval(() => {
    state.h5Reset = Math.max(0, state.h5Reset - 1);
    state.d7Reset = Math.max(0, state.d7Reset - 1);
    state.poll -= 1;

    if (state.poll <= 0) {
      state.poll = POLL_SECONDS;
      state.busy = true;
      el.widget.classList.add('busy');
      setTimeout(() => {
        state.busy = false;
        el.widget.classList.remove('busy');
        state.h5 += 0.6 + Math.random() * 1.4;
        state.d7 += 0.05;
        if (state.h5 >= 99) {           // the window reset, which is the point
          state.h5 = 8 + Math.random() * 6;
          state.h5Reset = 5 * 3600;
        }
        draw();
      }, BUSY_MS);
    }
    draw();
  }, 1000);
}

/* ──────────────────────────────────────────────── downloads, live */
const REPO = 'lucasmaziero/agent-gauge';

function slotFor(name) {
  if (name.endsWith('.sha256')) return null;
  if (name.endsWith('.exe')) return 'win';
  if (name.endsWith('.AppImage')) return 'linux';
  if (name.endsWith('.dmg')) return name.includes('arm64') ? 'arm64' : 'x86';
  return null;
}

async function fillDownloads() {
  let release;
  try {
    const response = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`);
    if (!response.ok) throw new Error(String(response.status));
    release = await response.json();
  } catch {
    return;              // the cards already link to the releases page
  }

  const version = document.getElementById('hero-version');
  if (version && release.tag_name) version.textContent = release.tag_name;

  for (const asset of release.assets || []) {
    const slot = slotFor(asset.name);
    if (!slot) continue;
    const card = document.querySelector(`.card[data-slot="${slot}"]`);
    if (!card) continue;

    card.href = asset.browser_download_url;
    card.querySelector('.file').textContent = asset.name;
    card.querySelector('.size').textContent = `${(asset.size / 1048576).toFixed(1)} MB`;
  }
}

/* ───────────────────────────────────────────────────────────  boot */
// ?lang=en wins over both the stored choice and the browser's, so a link can
// be shared in a known language.
const asked = new URLSearchParams(location.search).get('lang');
const stored = store.get('lang');
const initial = asked || stored || ((navigator.language || 'en').startsWith('pt') ? 'pt' : 'en');
setLanguage(STRINGS[initial] ? initial : 'en');
for (const button of document.querySelectorAll('.lang button')) {
  button.addEventListener('click', () => setLanguage(button.dataset.lang));
}
startWidget();
fillDownloads();
