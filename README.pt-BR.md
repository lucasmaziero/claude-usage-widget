<div align="center">

# Claude Usage Widget

**Seus limites do Claude Code num widget flutuante na área de trabalho.**

[English](README.md) · **Português**

[![CI](https://github.com/lucasmaziero/claude-usage-widget/actions/workflows/ci.yml/badge.svg)](https://github.com/lucasmaziero/claude-usage-widget/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/lucasmaziero/claude-usage-widget)](https://github.com/lucasmaziero/claude-usage-widget/releases/latest)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

<img src="docs/widget.png" width="440" alt="Widget flutuante mostrando 41% da janela de 5 horas">

</div>

---

## Como funciona

A API da Anthropic não expõe endpoint de consulta de uso para contas de assinatura. A utilização
viaja de carona nos headers `anthropic-ratelimit-unified-*` de qualquer resposta, então o widget faz
um `POST /v1/messages` mínimo, com `max_tokens: 1`, só para lê-los:

| Header | Vira |
| --- | --- |
| `unified-5h-utilization` | porcentagem da janela de 5 horas |
| `unified-7d-utilization` | porcentagem da janela de 7 dias |
| `unified-5h-reset` / `unified-7d-reset` | relógio e contagem regressiva de cada reset |
| `unified-status` / `representative-claim` | chip de status e qual janela é o gargalo |

Duas consequências de o app rodar na **mesma máquina** que o Claude Code:

- **Nada para configurar.** O token OAuth sai de `%USERPROFILE%\.claude\.credentials.json`, o mesmo
  arquivo que o Claude Code usa, relido a cada ciclo. Quando o Claude Code renova o token, o widget
  acompanha sozinho.
- **Contagem real de tokens.** Os headers só dizem porcentagem; os números absolutos existem apenas
  nos transcripts em `~/.claude/projects/**/*.jsonl`, que são lidos direto do disco.

## Instalação

Baixe o `ClaudeUsage-Setup-<versão>.exe` na [página de releases][releases] e dê dois cliques. A
instalação é **por usuário**, em `%LOCALAPPDATA%\Programs\Claude Usage Widget`. Não pede admin nem
passa por UAC. O assistente oferece atalho na área de trabalho e iniciar junto com o Windows, ambos
opcionais. Desinstala pelo painel **Aplicativos instalados**, perguntando antes se deve apagar
também suas preferências.

O instalador não é assinado, então o SmartScreen avisa "editor desconhecido" no primeiro download.
O SHA-256 é publicado junto de cada release para quem quiser validar o arquivo.

Requer um login prévio do Claude Code na máquina (`claude` uma vez). Sem isso o widget mostra
`.credentials.json não existe: faça login com claude uma vez`.

[releases]: https://github.com/lucasmaziero/claude-usage-widget/releases/latest

### Do código-fonte

```powershell
uv sync
uv run claude-usage      # ou .\run.bat, que sobe sem janela de console
```

## Uso

<img src="docs/panel.png" width="380" align="right" alt="Painel expandido">

**Widget.** Nenhum número aparece duas vezes: o anel responde *quanto já gastei da janela de 5h*, a
linha `5h` responde *quanto falta para ela resetar* (com o horário do reset à direita) e a linha `7d`
cobre a semana.

Em volta do anel corre um segundo anel, cinza sobre trilho, descontando até a próxima coleta, e ele
vira um giro verde enquanto a coleta acontece. O cinza é proposital: em uso alto o medidor fica
laranja ou vermelho, e um anel concêntrico da mesma família de cor se funde com ele.

A coluna da direita tem três andares: o mascote no topo, o botão de **atualizar agora** no meio e o
menu embaixo. Arraste o resto do cartão para posicionar (a posição fica salva), clique para abrir o
painel, ou use o botão direito em qualquer lugar para o menu.

**Painel.** A janela de 5h é o que morde primeiro, então fica num cartão com número grande e
medidor de 18 segmentos; a de 7 dias é apoio e vive solta sobre a superfície, com barra contínua.
Abaixo de um fio divisor vêm os metadados: chip de status (`OK` / `ATENÇÃO` / `BLOQUEADO`), tokens
reais da janela, incidentes abertos em `status.claude.com` e o carimbo da última coleta.

O mascote do cabeçalho acinzenta quando há erro de coleta ou incidente aberto, o mesmo sinal que o
selo do widget dá.

**Bandeja.** O ícone é o anel com o número dentro, desenhado num tamanho por vez para o shell não
precisar reduzir nada, inclusive nos tamanhos que a escala do monitor pede (25px a 125%). O tooltip
traz as duas janelas.

<br clear="right">

<div align="center"><img src="docs/tray.png" width="260" alt="Ícone da bandeja em 6%, 47%, 83% e 100%"></div>

### Menu

| Item | O que faz |
| --- | --- |
| Atualizar agora | Força um ciclo fora do intervalo |
| Abrir painel | Mesmo que clicar no widget |
| Mostrar widget | Deixa só o ícone da bandeja |
| Modo compacto | Reduz o widget ao anel |
| Travar posição | Ignora o arrasto |
| Intervalo | 30 s a 15 min, padrão 2 min |
| Idioma | Automático, Português, English |
| Iniciar com o Windows | Grava a entrada em `HKCU\...\CurrentVersion\Run` |

Preferências ficam em `%APPDATA%\ClaudeUsageWidget\settings.json`.

### Idioma

A interface vem em português e inglês. Por padrão segue o idioma do Windows; o menu tem **Idioma**
com Automático, Português e English, e a escolha fica salva nas preferências. A troca vale na hora,
sem reiniciar.

Não é só rótulo: o dia da semana (`sex` / `Fri`), o separador decimal (`6,0M` / `6.0M`) e o plural
de sessões acompanham o idioma. Traduzir só os rótulos deixa o resultado meio convertido, que é pior
que não traduzir.

As strings ficam em `src/claude_usage/i18n.py`, um dicionário por idioma. Acrescentar um idioma é
copiar o dicionário do inglês, traduzir os valores e registrar em `LANGUAGES`; um teste garante que
as chaves e os campos de formatação `{assim}` batem entre todos os idiomas.

## Estrutura

```
src/claude_usage/   código do app       tests/       suíte de testes
installer/          empacotamento       tools/       geradores de ícone e preview
```

| Módulo | Papel |
| --- | --- |
| `credentials.py` | Lê o token OAuth do Claude Code |
| `api.py` | Consulta de uso e incidentes; `parse()` separado para testar sem rede |
| `tokens.py` | Soma tokens da janela pelos transcripts locais |
| `poller.py` | Thread de coleta, histórico, burn rate e projeção |
| `theme.py` | Paleta, escala de espaçamento de 4pt e formatadores |
| `paint.py` | Primitivas de desenho: anel, medidor, chip, sombra, ícones |
| `brand.py` | Mascote do Claude Code a partir do SVG oficial, embutido como string |
| `i18n.py` | Strings da interface, um dicionário por idioma |
| `widget.py` | Barra flutuante |
| `panel.py` | Painel expandido |
| `app.py` | Bandeja, menu e montagem |

## Desenvolvimento

```powershell
uv sync                                           # cria o .venv com o grupo de dev
uv run pytest                                     # 81 testes, sem rede e sem janela
uv run ruff check .                               # lint (regras em pyproject.toml)
uv run python tools/preview.py docs/preview.png   # render offline das duas telas
$env:CLAUDE_USAGE_DEBUG=1; uv run claude-usage    # imprime cada ciclo no console
```

Os testes de render usam `QT_QPA_PLATFORM=offscreen` (ver `tests/conftest.py`) e verificam que todo
caminho de pintura roda sem estourar nos estados reais: sem dado, ao vivo, erro, coletando e modo
compacto.

Nesse modo o Qt troca o banco de fontes do Windows por um stub cuja fonte de fallback é ~1,8x mais
larga que a Segoe UI. Duas consequências:

- os testes que medem geometria de texto ficam condicionados à fonte real (fixture `real_fonts`) e
  se pulam no modo headless. Para rodar a suíte inteira contra a fonte de verdade:
  `$env:QT_QPA_PLATFORM = "windows"; uv run pytest`;
- o `tools/preview.py` **não** usa offscreen de propósito: nesse modo todo glifo vira quadradinho.

## Gerando o instalador

```powershell
.\installer\build.ps1                  # ícone -> PyInstaller -> Inno Setup
.\installer\build.ps1 -SkipInstaller   # só a pasta portátil em build\dist
.\installer\build.ps1 -Clean           # apaga build\ antes, inclusive os caches
```

Precisa do Inno Setup (`winget install JRSoftware.InnoSetup`); o script procura tanto a instalação
por usuário quanto a de máquina. Saída em `build\ClaudeUsage-Setup-<versão>.exe`, cerca de 21 MB
comprimidos para 70 MB instalados. Cada execução deixa **um único** setup na pasta, o recém-gerado:
guardar versões antigas lado a lado é como se distribui o `.exe` errado por engano.

| Arquivo | Papel |
| --- | --- |
| `installer/build.ps1` | Orquestra os três passos e lê a versão do `pyproject.toml` |
| `installer/claude-usage.spec` | PyInstaller: onedir, sem console, ícone e version resource |
| `installer/claude-usage.iss` | Inno Setup: instalação por usuário, atalhos, autostart, desinstalador |
| `installer/entry.py` | Entry point do build congelado (o `__main__.py` usa import relativo) |
| `tools/gen_icon.py` | Gera o `.ico` multi-resolução a partir do SVG do mascote |

Três decisões do empacotamento:

- **onedir, não onefile.** O `--onefile` descompacta todo o runtime do Qt no `%TEMP%` a cada
  execução, um a dois segundos num app que mora na bandeja e sobe com o Windows.
- **`opengl32sw.dll` fora do pacote.** São 20 MB do OpenGL por software da Mesa, um quinto do
  bundle, e esta interface é pintada só pelo raster engine do Qt.
- **`.ico` montado à mão.** Importar Pillow no mesmo processo do PySide6 carrega uma segunda
  libpng/zlib e o encoder PNG do Qt morre com violação de acesso; escrever o contêiner ICO são 40
  linhas e elimina a classe inteira de conflito de DLL.

## Notas de implementação

Coisas que custaram tempo e que o código sozinho não explica:

- **`QGraphicsDropShadowEffect` em janela translúcida no Windows congela o conteúdo** depois do
  primeiro frame, e o widget desenhava `--` para sempre. A sombra é pintada à mão em `paint.shadow()`
  e cada janela reserva uma margem transparente para ela.
- **O receptor dos sinais do poller precisa ser `QObject`.** Ligado a um objeto Python comum, a
  conexão vira direta e o desenho acontece na thread da coleta.
- **Clicar no widget com o painel aberto chega em duas partes.** O `Qt.Popup` se fecha sozinho no
  clique de fora e o widget recebe o mesmo clique em seguida; sem guarda, o painel fechava e reabria
  no mesmo gesto. `Panel.just_closed()` engole o segundo evento por 250 ms.
- **Texto é medido, nunca posicionado por deslocamento fixo.** `56min` é meia vez mais largo que
  `2h13` e invadia a coluna do relógio. Os algarismos usam `tnum` (`QFont.setFeature`), senão o `1`
  é mais estreito que os outros dígitos e a contagem treme a cada segundo.

## Custo

Cada ciclo é um POST de 1 token de saída. A 2 minutos, são cerca de 700 requisições por dia, todas
do menor tamanho possível. Se incomodar, aumente o intervalo no menu.

## Licença

MIT. Veja [LICENSE](LICENSE).
