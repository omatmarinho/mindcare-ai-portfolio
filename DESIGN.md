---
version: 1.0
name: MindCare-AI
description: Interface de consultório para psicólogos. Verde-floresta profundo como cor principal, dourado quente para destaques e pontos de atenção, fundo creme-sálvia com cartões brancos arredondados. Visual de painel (dashboard) calmo e organizado, que transmite cuidado e sigilo, sem cara de software hospitalar nem de app de marketing. Fonte sem serifa (Geist) em toda a interface.

colors:
  primary: "#46603a"          # brand-600: botões, menu ativo, anel de progresso, logo
  primary-hover: "#3a4f31"    # brand-700
  primary-strong: "#2d3f27"   # brand-800: painel do login, cartão "Nova consulta" do menu
  primary-deep: "#1c3426"     # brand-900: texto sobre dourado
  primary-soft: "#f2f5ef"     # brand-50: fundo de destaque suave, status "Agendada"
  primary-tint: "#e2e9dc"     # brand-100: trilho do anel, dias com consultas
  primary-line: "#c6d4bb"     # brand-200: bordas de destaque
  accent: "#f2a51d"           # accent-500: botão "Agendar", ponto de "hoje"
  accent-soft: "#fef8ea"      # accent-50: fundo de atenção
  accent-tint: "#fcecc6"      # accent-100: avatar, ícone de atenção
  accent-light: "#f6c860"     # accent-300: ícone do menu ativo, dourado sobre verde
  accent-strong: "#a4670b"    # accent-700: texto/valor de atenção (contraste AA sobre branco)
  canvas: "#edefe9"           # fundo da aplicação (creme-sálvia)
  surface: "#ffffff"          # cartões, menu lateral, barra do topo
  surface-muted: "#f8f9f6"    # gray-50: linhas de lista, áreas internas
  hairline: "#e4e6df"         # gray-200: bordas de cartão (com 70% de opacidade)
  ink: "#1d2420"              # gray-900: títulos e valores
  body: "#43463e"             # gray-700: texto corrido
  muted: "#767a6f"            # gray-500: legendas, rótulos
  muted-soft: "#a3a79c"       # gray-400: ícones inativos, placeholders
  success: "#047857"          # emerald-700: "Pago", "Realizada", valores recebidos
  danger: "#b91c1c"           # red-700: erros, "Vencido", ações destrutivas
  on-primary: "#ffffff"

typography:
  page-title:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: -0.4px
  card-title:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.4
  kpi-value:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.4px
    fontVariantNumeric: tabular-nums
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
  section-label:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 11px
    fontWeight: 500
    letterSpacing: 0.6px
    textTransform: uppercase
  button:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1
  code:
    fontFamily: "Geist Mono, ui-monospace, monospace"
    fontSize: 13px

rounded:
  sm: 8px        # botões, campos, badges de tabela (rounded-lg)
  md: 12px       # itens do menu, linhas de lista, busca do topo (rounded-xl)
  lg: 16px       # cartões, menu lateral (rounded-2xl)
  full: 9999px   # badges de status, avatar, ícones de KPI

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  gutter-mobile: 16px
  gutter-desktop: 32px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    hoverColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.sm}"
    padding: 8px 16px
  button-secondary:
    backgroundColor: "{colors.surface}"
    borderColor: "#d0d3ca"
    textColor: "{colors.body}"
    rounded: "{rounded.sm}"
  button-ghost:
    backgroundColor: transparent
    hoverColor: "{colors.primary-soft}"
    textColor: "{colors.primary-hover}"
  button-danger:
    backgroundColor: "{colors.surface}"
    borderColor: "#fecaca"
    textColor: "{colors.danger}"
  button-accent:
    backgroundColor: "{colors.accent}"
    hoverColor: "{colors.accent-light}"
    textColor: "{colors.primary-deep}"
    usage: "Só no cartão escuro do menu lateral (Agendar). Não usar em telas comuns."
  card:
    backgroundColor: "{colors.surface}"
    border: "1px solid {colors.hairline} @ 70%"
    rounded: "{rounded.lg}"
    padding: 20px (24px a partir de 640px)
    shadow: "0 1px 2px rgba(29,36,32,0.04)"
  card-highlight:
    backgroundColor: "{colors.primary-soft}"
    borderColor: "{colors.primary-line}"
  sidebar:
    backgroundColor: "{colors.surface}"
    width: 240px
    inset: 12px
    rounded: "{rounded.lg}"
  nav-item-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    iconColor: "{colors.accent-light}"
    rounded: "{rounded.md}"
  input:
    backgroundColor: "{colors.surface}"
    borderColor: "#d0d3ca"
    focusBorder: "{colors.primary}"
    focusRing: "3px {colors.primary} @ 15%"
    rounded: "{rounded.sm}"
  badge:
    rounded: "{rounded.full}"
    padding: 2px 10px
    typography: "{typography.caption}"
  ring-progress:
    track: "{colors.primary-tint}"
    fill: "{colors.primary}"
    size: 76px
    strokeWidth: 7px
---

# MindCare AI: guia visual

Este arquivo descreve o visual **atual** do MindCare AI. As cores e classes reais estão em
`frontend/src/app/globals.css` (tokens `brand-*`, `accent-*`, `gray-*`, `canvas`) e nos componentes
compartilhados. Se este guia e o código divergirem, o código vale e este arquivo deve ser atualizado.

## Visão geral

Quem usa é o psicólogo, durante o dia de atendimentos: precisa ver rápido a agenda de hoje, os
registros que a IA rascunhou e o que precisa de atenção. O visual deve passar **calma,
cuidado e sigilo**. Por isso:

- **Verde-floresta** como cor principal (natureza, equilíbrio), sobre um fundo **creme-sálvia** que
  não cansa a vista em jornadas longas.
- **Dourado** só para chamar atenção (cobrança vencida, registro esperando revisão, "hoje").
  Se tudo for dourado, nada chama atenção.
- **Layout de painel**: menu lateral flutuante, barra do topo com busca e o usuário, cartões
  brancos arredondados. Informação resumida primeiro, detalhe depois.
- Nada de fotos de banco de imagens, ilustrações chamativas, gradientes fortes ou animações
  decorativas. O conteúdo (pacientes, horários, valores) é o protagonista.

## Cores

### Principal e destaque
- `brand-600` **#46603a** é a cor de ação: botão primário, item ativo do menu, anel de progresso.
- `brand-800` **#2d3f27** é a superfície escura: painel da marca no login e o cartão "Nova consulta".
- `accent-500` **#f2a51d** aparece em poucos pontos. Para **texto** dourado sobre branco use
  `accent-700` **#a4670b**, que tem contraste suficiente; o 500 é só para preenchimentos.

### Superfícies
- Fundo da aplicação: `canvas` **#edefe9**. Cartões, menu e barra do topo: branco.
- Áreas internas de um cartão (linhas de lista, hora da consulta): `gray-50` **#f8f9f6**.

### Texto
- Títulos e números: `gray-900`. Texto corrido: `gray-700`. Rótulos e legendas: `gray-500`.
- Os cinzas puxam levemente para o verde; não usar cinzas neutros ou azulados do Tailwind padrão.

### Semânticas (sempre com texto, nunca só cor)
| Situação | Estilo |
|---|---|
| Agendada | fundo `brand-50`, borda `brand-200`, texto `brand-800` |
| Realizada / Pago | `emerald-50` / `emerald-200` / `emerald-800` |
| Faltou / atenção | `accent-50` / `accent-300` / `accent-700` |
| Cancelada | cinza, texto riscado |
| Vencido / erro | `red-50` / `red-200` / `red-700` |

## Tipografia

- Uma família só: **Geist** (carregada pelo `next/font`), com Geist Mono para códigos.
- Hierarquia: título da página 24px/600 → título do cartão 16px/600 → texto 14px → legenda 12px.
- Números de KPI em 24px/600 com `tabular-nums`. Horários e valores alinhados também usam
  `tabular-nums`.
- Rótulos de seção ("MENU") em 11px, caixa alta, espaçamento de letra leve.
- Textos em português do Brasil, frases curtas, voz ativa, tratando o usuário por "você".
  Botões dizem a ação ("Cadastrar paciente", "Salvar e aprovar"), nunca "OK" ou "Continuar".

## Layout

### Estrutura
- **Computador (≥1024px)**: menu lateral fixo de 240px, flutuando a 12px das bordas; conteúdo
  à direita com largura máxima de 1280px; barra do topo com busca de paciente e o cartão do usuário.
- **Celular**: barra superior com a logo e botão de menu; o menu abre por baixo e fecha ao navegar.
  Margem lateral de 16px. Nenhuma tela pode rolar para o lado.

### Grade
- KPIs: 1 coluna no celular, 2 a partir de 640px, 4 a partir de 1280px.
- Conteúdo principal + coluna lateral: `lg:grid-cols-3` (2 + 1).
- Espaço entre blocos: 24px. Dentro de cartões: 16–20px.

## Elevação e profundidade

Quase plano. A separação vem do contraste branco sobre creme-sálvia e de bordas suaves.
Sombra só a mínima (`0 1px 2px` com 4% de opacidade). Nada de sombras grandes ou cartões
"flutuando" com blur.

## Formas

- Cartões e menu: 16px. Itens de menu e linhas de lista: 12px. Botões e campos: 8px.
- Badges de status, avatares e ícones de KPI: totalmente redondos.

## Componentes

Os componentes reais ficam em `frontend/src/components/`:

- `page.tsx`: `PageHeader` (título, subtítulo, ações, link "voltar"), `Card`, `EmptyState`, `Badge`.
- `ui.tsx`: `Field`, `SubmitButton` (com indicador de carregamento), `ConfirmSubmit` (confirmação
  antes de ações irreversíveis), `Alert`.
- `charts.tsx`: `Ring` (anel de progresso) e `MonthCalendar` (calendário do mês).
- `lib/ui-classes.ts`: `buttonClasses(variant, size)` e `inputClasses`. Use sempre essas funções
  em vez de repetir classes de botão e campo.

### Botões
- **Primário** (verde): uma ação principal por tela ou por cartão.
- **Secundário** (branco com borda): ações alternativas.
- **Ghost** (só texto verde): links de ação dentro de cartões ("Ver agenda").
- **Perigo** (texto vermelho): sempre via `ConfirmSubmit`, nunca com efeito imediato.

### Cartões
- Título 16px/600 opcional, descrição em cinza, ações no canto direito.
- Cartão de destaque (`brand-50`) só para o KPI principal da tela.

### KPI
- Rótulo em cinza, valor grande, linha de detalhe. Ícone em círculo à direita (`brand-50`, ou
  `accent-100` quando pede atenção). O KPI principal pode trocar o ícone por um `Ring`.

### Telas vazias
- Sempre explicam o que vai aparecer ali e oferecem a próxima ação ("Cadastrar paciente").

## Faça

- Use os tokens `brand-*`, `accent-*`, `gray-*` e `canvas`; nunca cores hexadecimais soltas.
- Mostre o estado com texto **e** cor (badge "Vencido", não só vermelho).
- Peça confirmação antes de arquivar, cancelar, excluir, revogar ou aprovar.
- Mostre um esqueleto de carregamento (`loading.tsx`) em cada seção.
- Formate datas, horas e dinheiro com `Intl` em pt-BR e fuso America/Sao_Paulo.

## Não faça

- Não usar dourado em botões comuns nem em grandes áreas.
- Não criar telas com fundo escuro ou gradientes chamativos na área logada.
- Não usar fotos de pessoas, emojis ou ilustrações decorativas.
- Não colocar dados reais de pacientes em exemplos, protótipos ou capturas de tela; use nomes
  fictícios ("Ana Ficticia Souza").
- Não sugerir diagnóstico na interface: textos da IA são sempre "rascunho para sua revisão".

## Responsividade

### Pontos de quebra (Tailwind)
| Nome | Largura | O que muda |
|---|---|---|
| base | < 640px | 1 coluna, menu recolhido, status aparece junto do texto |
| sm | ≥ 640px | KPIs em 2 colunas, badges de status visíveis |
| lg | ≥ 1024px | menu lateral fixo, barra do topo, grade 2 + 1 |
| xl | ≥ 1280px | KPIs em 4 colunas |

### Toque
- Alvos de toque com pelo menos 40px de altura (itens do menu, linhas de lista, dias do calendário).
- Tabelas largas rolam dentro do próprio cartão (`overflow-x-auto`), nunca a página.

## Como evoluir este guia

1. Mudou uma cor ou componente no código? Atualize a seção correspondente aqui no mesmo commit.
2. Componente novo usado em mais de uma tela vai para `components/` e ganha uma linha em
   "Componentes".
3. Antes de publicar uma tela nova, confira no celular (390px) e rode a revisão
   `web-design-guidelines`.

## Lacunas conhecidas

- Não há tema escuro.
- O painel da marca no login ainda não tem ilustração própria (só formas suaves ao fundo).
- Gráficos de linha ou de barras (ex.: receita por mês) ainda não existem; quando existirem,
  devem usar `brand-600` como série principal e `accent-500` só para destaque.
