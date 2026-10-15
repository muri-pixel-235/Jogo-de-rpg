"""Interface Pygame: menus, preparação, batalha e ferramentas de desenvolvimento."""
from __future__ import annotations

import json
import random
from pathlib import Path

import pygame

from batalha import (ATAQUES, CHANCE_SECRETO, CLASSES, CLIMAS, CONTRATOS, DIFICULDADES, EFEITOS,
                     INIMIGOS, ITENS, RELIQUIAS, RELIQUIAS_INIMIGO)
from .engine import Battle, Fighter, make_enemy, make_player

WIDTH, HEIGHT = 1280, 760
ROOT = Path(__file__).resolve().parent.parent
BG = (14, 19, 31)
PANEL = (25, 34, 52)
PANEL2 = (33, 45, 67)
TEXT = (235, 241, 250)
MUTED = (151, 169, 191)
CYAN = (74, 211, 220)
GOLD = (255, 196, 91)
RED = (230, 93, 112)
GREEN = (93, 210, 145)
BLUE = (103, 155, 255)


class Button:
    def __init__(self, rect, label, action, *, fill=PANEL2, accent=CYAN, enabled=True):
        self.rect, self.label, self.action = pygame.Rect(rect), label, action
        self.fill, self.accent, self.enabled = fill, accent, enabled

    def draw(self, surface, font, mouse):
        hover = self.rect.collidepoint(mouse) and self.enabled
        color = tuple(min(255, c + (10 if hover else 0)) for c in self.fill)
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, self.accent if self.enabled else MUTED, self.rect, 2, border_radius=12)
        label = font.render(self.label, True, TEXT if self.enabled else MUTED)
        max_width = self.rect.width - 18
        if label.get_width() > max_width:
            label = pygame.transform.smoothscale(label, (max_width, label.get_height()))
        surface.blit(label, label.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


class RPGApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("RPG de Batalha — Pygame")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 18)
        self.small = pygame.font.SysFont("segoeui", 14)
        self.medium = pygame.font.SysFont("segoeui", 24, bold=True)
        self.large = pygame.font.SysFont("segoeui", 44, bold=True)
        self.running = True
        self.page = "home"
        self.buttons: list[Button] = []
        self.mode = "solo"
        self.team_size = 1
        self.setup_step = 0
        self.setup_name = "Aventureiro"
        self.setup_class = "cavaleiro"
        self.setup_relic = "nenhum"
        self.opponent_name = "morcego"
        self.setup_focus = "player_name"
        self.setup_inputs = ["", "", "", "", "", "", "", ""]
        self.setup_player_classes = ["cavaleiro", "mago", "arqueiro", "velocista"]
        self.setup_player_enemies = ["morcego"] * 4
        self.setup_player_is_enemy = [False] * 4
        self.setup_foe_classes = ["morcego", "golem de gelo", "esqueleto guerreiro", "mestre mago"]
        self.setup_slot = 0
        self.rival_slots = ["cavaleiro", "mago", "arqueiro", "velocista"]
        self.rival_is_enemy = [False] * 4
        self.setup_relics = ["nenhum"] * 8
        self.enemy_scroll = 0
        self.class_scroll = 0
        self.relic_scroll = 0
        self.attack_page = 0
        self.item_page = 0
        self.battle: Battle | None = None
        self.dev_battle: Battle | None = None
        self.inventory: dict[str, int] = {}
        self.pending_attack: str | None = None
        self.pending_item: str | None = None
        self.pending_contract = False
        self.selected_target: Fighter | None = None
        self.notice = ""
        self.notice_until = 0
        self.history_scroll = 0
        self.dev_input = ""
        self.dev_auth_stage: str | None = None
        self.dev_auth_input = ""
        self.dev_waiting_confirmation: str | None = None
        self.dev_failing: list[str] = []
        self.dev_working: list[str] = []
        self.dev_dummy: Fighter | None = None
        self.setup_name_index = 0
        self.prompt_category = "Personagem"
        self.prompt_name = ""
        self.prompt_description = ""
        self.prompt_result = ""
        self.prompt_field = "name"
        self.load_dev_results()

    def load_dev_results(self):
        path = ROOT / "dev_test_results.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.dev_working = payload.get("funcionando", [])
            self.dev_failing = payload.get("nao_funcionando", [])
        except (OSError, ValueError):
            pass

    def save_dev_results(self):
        path = ROOT / "dev_test_results.json"
        path.write_text(json.dumps({"funcionando": self.dev_working,
                                    "nao_funcionando": self.dev_failing},
                                   ensure_ascii=False, indent=2), encoding="utf-8")

    def notify(self, message: str):
        self.notice, self.notice_until = message, pygame.time.get_ticks() + 2600

    def text(self, value, x, y, color=TEXT, font=None):
        self.screen.blit((font or self.font).render(str(value), True, color), (x, y))

    def text_fit(self, value, x, y, width, color=TEXT, font=None):
        font = font or self.font
        rendered = font.render(str(value), True, color)
        if rendered.get_width() > width:
            rendered = pygame.transform.smoothscale(rendered, (width, rendered.get_height()))
        self.screen.blit(rendered, (x, y))

    def wrap(self, value: str, width: int, font=None) -> list[str]:
        font = font or self.font
        lines, current = [], ""
        for word in value.split():
            test = f"{current} {word}".strip()
            if font.size(test)[0] > width and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def paragraph(self, value: str, x: int, y: int, width: int, color=MUTED, font=None, limit=None):
        font = font or self.small
        lines = self.wrap(value, width, font)
        if limit:
            lines = lines[:limit]
        for i, line in enumerate(lines):
            self.text(line, x, y + i * (font.get_linesize() + 2), color, font)
        return y + len(lines) * (font.get_linesize() + 2)

    def panel(self, rect, title=None, accent=CYAN):
        r = pygame.Rect(rect)
        pygame.draw.rect(self.screen, PANEL, r, border_radius=18)
        pygame.draw.rect(self.screen, (50, 68, 94), r, 1, border_radius=18)
        if title:
            self.text(title, r.x + 18, r.y + 14, accent, self.medium)

    def add_button(self, rect, label, action, **kwargs):
        button = Button(rect, label, action, **kwargs)
        self.buttons.append(button)
        button.draw(self.screen, self.font, pygame.mouse.get_pos())

    def header(self, eyebrow, title, subtitle=""):
        self.text(eyebrow.upper(), 48, 26, CYAN, self.small)
        self.text_fit(title, 48, 48, self.screen.get_width() - 96, TEXT, self.large)
        if subtitle:
            self.text_fit(subtitle, 50, 106, self.screen.get_width() - 100, MUTED, self.font)

    def draw(self):
        self.screen.fill(BG)
        self.buttons = []
        if self.page == "home":
            self.draw_home()
        elif self.page == "settings":
            self.draw_settings()
        elif self.page == "setup":
            self.draw_setup()
        elif self.page == "battle":
            self.draw_battle()
        elif self.page == "briefing":
            self.draw_briefing()
        elif self.page == "results":
            self.draw_results()
        elif self.page == "dev":
            self.draw_dev()
        elif self.page == "prompts":
            self.draw_prompts()
        if self.notice and pygame.time.get_ticks() < self.notice_until:
            rect = pygame.Rect(340, HEIGHT - 60, WIDTH - 680, 42)
            pygame.draw.rect(self.screen, (46, 66, 84), rect, border_radius=12)
            self.screen.blit(self.font.render(self.notice, True, TEXT),
                             self.font.render(self.notice, True, TEXT).get_rect(center=rect.center))
        pygame.display.flip()

    def draw_home(self):
        # Fundo em camadas e brasão abstrato feito de formas vetoriais.
        pygame.draw.circle(self.screen, (24, 47, 67), (960, 265), 220)
        pygame.draw.circle(self.screen, (29, 65, 78), (960, 265), 160, 2)
        pygame.draw.polygon(self.screen, (41, 99, 111), [(960, 140), (1050, 220), (1020, 370), (960, 410), (900, 370), (870, 220)])
        pygame.draw.polygon(self.screen, (255, 206, 113), [(960, 184), (1007, 235), (990, 329), (960, 349), (930, 329), (913, 235)])
        self.text("ARENA  /  ELEMENTOS", 68, 85, CYAN, self.medium)
        self.text("RPG de", 64, 148, TEXT, self.large)
        self.text("Batalha", 64, 196, TEXT, self.large)
        self.paragraph("Monte seu grupo, escolha uma estratégia e enfrente batalhas por turnos em uma arena de fantasia.", 68, 267, 560, MUTED, self.font)
        self.add_button((68, 366, 250, 54), "Jogar", lambda: self.go_setup(), fill=(37, 94, 102))
        self.add_button((68, 432, 250, 48), "Configurações", lambda: self.go("settings"))
        self.add_button((68, 492, 250, 48), "Sair", lambda: setattr(self, "running", False), accent=RED)
        self.text("AVENTURA TÁTICA  •  TURNOS INDIVIDUAIS", 68, HEIGHT - 54, MUTED, self.small)
        self.text("P Y G A M E", 1086, HEIGHT - 54, CYAN, self.small)

    def draw_settings(self):
        self.header("Preferências", "Configurações", "Ajuste controles e acesse ferramentas de desenvolvimento.")
        self.panel((48, 168, 575, 430), "Jogo")
        self.paragraph("O protótipo usa desenho vetorial, resolução redimensionável e dados compartilhados com batalha.py.", 72, 226, 520)
        self.text("Resolução atual", 72, 306, TEXT)
        self.text(f"{self.screen.get_width()} × {self.screen.get_height()}", 72, 338, CYAN, self.medium)
        self.text("Controles", 72, 408, TEXT)
        self.paragraph("Mouse: escolher ações e alvos. Teclado: escrever nomes, prompts e comandos de teste.", 72, 440, 490)
        self.panel((650, 168, 582, 430), "Desenvolvimento", accent=GOLD)
        self.paragraph("Teste efeitos e terrenos contra um Dummy. A outra área organiza textos de prompt para criar imagens externamente; ela não gera imagens.", 676, 226, 510)
        self.add_button((678, 346, 500, 54), "Abrir Dev Tools / Ambiente de Teste", self.begin_dev_auth, accent=GOLD)
        self.add_button((678, 414, 500, 54), "Preparar prompts para imagens", lambda: self.go("prompts"))
        self.add_button((48, 640, 190, 48), "← Voltar", lambda: self.go("home"))
        if self.dev_auth_stage:
            pygame.draw.rect(self.screen, (0, 0, 0, 130), (0, 0, WIDTH, HEIGHT))
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((4, 8, 15, 190))
            self.screen.blit(veil, (0, 0))
            self.panel((350, 260, 580, 220), "Verificação de acesso", accent=GOLD)
            prompt = "Código de acesso" if self.dev_auth_stage == "code" else "Senha de confirmação"
            self.text(prompt + "  ·  pressione Enter", 380, 326, TEXT)
            masked = "•" * len(self.dev_auth_input)
            self.text(masked or "Digite o código", 380, 376, CYAN if masked else MUTED, self.medium)

    def go_setup(self):
        self.mode = "solo"
        self.team_size = 1
        self.setup_slot = 0
        self.go("setup")

    def begin_dev_auth(self):
        self.dev_auth_stage = "code"
        self.dev_auth_input = ""

    def submit_dev_auth(self):
        if self.dev_auth_stage == "code" and self.dev_auth_input == "@dev.mode_true":
            self.dev_auth_stage = "password"
            self.dev_auth_input = ""
        elif self.dev_auth_stage == "password" and self.dev_auth_input == "@dev.mode_segurity123":
            self.dev_auth_stage = None
            self.dev_auth_input = ""
            self.go("dev")
        else:
            self.dev_auth_stage = None
            self.dev_auth_input = ""
            self.notify("Acesso negado.")

    def draw_setup(self):
        self.header("Preparação", "Monte a batalha", "Escolha nome, classe e relíquia. No Multiplayer, configure também a Equipe B.")
        self.panel((48, 160, 312, 516), "Modo")
        for i, mode in enumerate(("solo", "dupla", "multiplayer")):
            label = {"solo": "Solo  •  1 × 1", "dupla": "Dupla  •  2 × 2", "multiplayer": "Multiplayer  •  PvP"}[mode]
            self.add_button((70, 216 + i * 62, 268, 48), label,
                            lambda m=mode: self.select_mode(m),
                            fill=(37, 94, 102) if self.mode == mode else PANEL2)
        self.text("Tamanho das equipes", 70, 430, TEXT)
        for count in range(1, 5):
            self.add_button((70 + (count - 1) * 64, 462, 54, 46), str(count),
                            lambda n=count: self.set_team_size(n),
                            fill=(37, 94, 102) if count == self.team_size else PANEL2,
                            enabled=(self.mode == "multiplayer"))
        if self.mode == "multiplayer":
            self.text("EQUIPE A", 70, 534, BLUE, self.small)
            self.text("EQUIPE B  /  inimigos", 70, 590, RED, self.small)
            for i in range(self.team_size):
                self.add_button((70 + i * 64, 554, 54, 32), f"A{i + 1}",
                                lambda n=i: self.select_setup_slot(n),
                                fill=(37, 94, 102) if self.setup_slot == i else PANEL2)
                rival_index = self.team_size + i
                self.add_button((70 + i * 64, 610, 54, 32), f"B{i + 1}",
                                lambda n=rival_index: self.select_setup_slot(n),
                                fill=(111, 47, 64) if self.setup_slot == rival_index else PANEL2,
                                accent=RED)
        else:
            self.paragraph("Escolha o nome, a classe e a relíquia de cada jogador. O inimigo será sorteado.", 70, 536, 260, MUTED, self.small)

        is_rival_slot = self.mode == "multiplayer" and self.setup_slot >= self.team_size
        count = (1 if self.mode == "solo" else 2) if self.mode != "multiplayer" else self.team_size * 2
        slot_number = self.setup_slot - self.team_size + 1 if is_rival_slot else self.setup_slot + 1
        side_index = self.setup_slot - self.team_size if is_rival_slot else self.setup_slot
        self.setup_name_index = 4 + side_index if is_rival_slot else side_index
        self.panel((384, 160, 848, 516), "Equipe B" if is_rival_slot else "Equipe A", accent=RED if is_rival_slot else BLUE)
        self.text(f"Personagem {slot_number} de {self.team_size if self.mode == 'multiplayer' else count}", 410, 218, GOLD, self.medium)
        if self.mode == "multiplayer":
            self.text("Este lado também pode usar classes ou personagens inimigos.", 410, 252, MUTED, self.small)
        self.input_box((410, 286, 390, 46), "Nome (clique e digite)", self.setup_inputs[self.setup_name_index], "player_name", hint="Digite seu próprio nome")
        if self.mode == "multiplayer":
            is_enemy_selection = self.rival_is_enemy[side_index] if is_rival_slot else self.setup_player_is_enemy[side_index]
            self.add_button((824, 286, 166, 46), "Classes", lambda: self.set_side_type(side_index, is_rival_slot, False),
                            fill=PANEL2 if not is_enemy_selection else PANEL)
            self.add_button((1000, 286, 204, 46), "Personagens inimigos", lambda: self.set_side_type(side_index, is_rival_slot, True),
                            fill=(111, 47, 64) if is_enemy_selection else PANEL, accent=RED)
        else:
            is_enemy_selection = False
        self.text("PERSONAGEM", 410, 346, BLUE if not is_rival_slot else RED, self.small)
        self.text("RELÍQUIAS", 842, 346, GOLD, self.small)
        selected_character = (self.rival_slots[side_index] if is_rival_slot else
                              self.setup_player_enemies[side_index] if is_enemy_selection else
                              self.setup_player_classes[side_index])
        if is_enemy_selection:
            enemy_names = list(INIMIGOS)
            page_size = 8
            page_count = max(1, (len(enemy_names) + page_size - 1) // page_size)
            self.enemy_scroll = min(self.enemy_scroll, page_count - 1)
            visible = enemy_names[self.enemy_scroll * page_size:(self.enemy_scroll + 1) * page_size]
            for i, enemy_name in enumerate(visible):
                col, row = i % 2, i // 2
                data = INIMIGOS[enemy_name]
                ability = data.get("habilidade", {}).get("nome", "Sem habilidade")
                detail = f"HP {data.get('vida', 0)}  DEF {data.get('defesa', 0)}  VEL {data.get('velocidade', 0)}\nHabilidade: {ability}"
                action = lambda n=enemy_name: self.select_side_character(side_index, n, is_rival_slot, True)
                self.choice_card((410 + col * 207, 370 + row * 62, 198, 56), enemy_name, detail,
                                 selected_character == enemy_name, action, RED)
            self.add_button((410, 626, 96, 30), "Anterior", lambda: self.scroll_enemies(-1), enabled=self.enemy_scroll > 0)
            self.text(f"Página {self.enemy_scroll + 1}/{page_count}  ·  {len(enemy_names)} personagens", 516, 633, MUTED, self.small)
            self.add_button((730, 626, 96, 30), "Próxima", lambda: self.scroll_enemies(1), enabled=self.enemy_scroll < page_count - 1)
            relic_options = ["nenhum", *RELIQUIAS_INIMIGO]
            relic_label = "Relíquias para inimigos"
        else:
            classes = list(CLASSES)
            class_page_size = 4
            class_page_count = max(1, (len(classes) + class_page_size - 1) // class_page_size)
            self.class_scroll = min(self.class_scroll, class_page_count - 1)
            visible_classes = classes[self.class_scroll * class_page_size:(self.class_scroll + 1) * class_page_size]
            for i, class_name in enumerate(visible_classes):
                col, row = i % 2, i // 2
                data = CLASSES[class_name]
                ability = data.get("habilidade", {}).get("nome", "Sem habilidade")
                attacks = ", ".join(data.get("ataques", [])[:2]) or "Sem ataques"
                detail = (f"HP {data.get('vida', 0)}  EN {data.get('energia', 0)}\n"
                          f"VEL {data.get('velocidade', 0)}  CRIT {data.get('critico', 0)}%\n"
                          f"Habilidade: {ability}\nAtaques: {attacks}")
                action = lambda n=class_name: self.select_side_character(side_index, n, is_rival_slot, False)
                self.choice_card((410 + col * 207, 372 + row * 126, 198, 116), class_name,
                                 detail, selected_character == class_name, action, BLUE)
            self.add_button((410, 626, 96, 30), "Anterior", lambda: self.scroll_classes(-1), enabled=self.class_scroll > 0)
            self.text(f"Página {self.class_scroll + 1}/{class_page_count} · {len(classes)} classes", 516, 633, MUTED, self.small)
            self.add_button((730, 626, 96, 30), "Próxima", lambda: self.scroll_classes(1), enabled=self.class_scroll < class_page_count - 1)
            relic_options = ["nenhum", *RELIQUIAS]
            relic_label = "Relíquias para classes"
        self.text(relic_label, 842, 365, MUTED, self.small)
        relic_index = 4 + side_index if is_rival_slot else side_index
        selected_relic = self.setup_relics[relic_index]
        relic_page_size = 6
        relic_page_count = max(1, (len(relic_options) + relic_page_size - 1) // relic_page_size)
        self.relic_scroll = min(self.relic_scroll, relic_page_count - 1)
        visible_relics = relic_options[self.relic_scroll * relic_page_size:(self.relic_scroll + 1) * relic_page_size]
        for i, relic_name in enumerate(visible_relics):
            col, row = i % 2, i // 2
            relic_data = (RELIQUIAS_INIMIGO if is_enemy_selection else RELIQUIAS).get(relic_name, {})
            description = relic_data.get("descricao", "Sem relíquia")
            self.choice_card((842 + col * 180, 388 + row * 80, 172, 72), relic_name,
                             description, selected_relic == relic_name,
                             lambda n=relic_name: self.select_setup_relic(relic_index, n), GOLD)
        self.add_button((842, 626, 84, 30), "Ant. rel.", lambda: self.scroll_relics(-1), enabled=self.relic_scroll > 0)
        self.text(f"Rel. {self.relic_scroll + 1}/{relic_page_count}", 934, 633, MUTED, self.small)
        self.add_button((1022, 626, 84, 30), "Próx. rel.", lambda: self.scroll_relics(1), enabled=self.relic_scroll < relic_page_count - 1)
        if self.mode == "multiplayer":
            self.add_button((972, 626, 230, 34), "Iniciar batalha", self.start_setup_battle)
        else:
            if count > 1:
                self.add_button((410, 626, 112, 34), "Anterior", lambda: self.change_slot(-1), enabled=self.setup_slot > 0)
            self.add_button((972, 626, 230, 34), "Próximo" if self.setup_slot + 1 < count else "Iniciar batalha", self.next_setup)
        self.add_button((48, 700, 170, 42), "Menu", lambda: self.go("home"))

    def choice_card(self, rect, title, description, selected, action, accent):
        card = pygame.Rect(rect)
        fill = (43, 74, 89) if selected and accent == BLUE else (91, 55, 67) if selected and accent == RED else (75, 65, 43) if selected else PANEL2
        pygame.draw.rect(self.screen, fill, card, border_radius=10)
        pygame.draw.rect(self.screen, accent if selected else (57, 74, 96), card, 2 if selected else 1, border_radius=10)
        self.text_fit(title, card.x + 10, card.y + 7, card.w - 20, accent if selected else TEXT, self.small)
        detail_lines = []
        for source_line in description.splitlines():
            detail_lines.extend(self.wrap(source_line, card.w - 20, self.small))
        y = card.y + 26
        max_lines = 4 if card.h > 100 else 2
        for line in detail_lines[:max_lines]:
            self.text(line, card.x + 10, y, MUTED, self.small)
            y += 16
        self.buttons.append(Button(card, "", action, fill=(0, 0, 0), accent=(0, 0, 0)))

    def select_setup_slot(self, index):
        self.setup_slot = index
        if self.mode == "multiplayer" and index >= self.team_size:
            self.setup_name_index = 4 + index - self.team_size
        else:
            self.setup_name_index = index
        self.setup_focus = "player_name"

    def select_side_character(self, side_index, name, is_rival, is_enemy):
        if is_rival:
            self.rival_slots[side_index] = name
        elif is_enemy:
            self.setup_player_enemies[side_index] = name
        else:
            self.setup_player_classes[side_index] = name

    def set_side_type(self, side_index, is_rival, is_enemy):
        if is_rival:
            self.set_rival_type(side_index, is_enemy)
        else:
            self.setup_player_is_enemy[side_index] = is_enemy
            if is_enemy and self.setup_player_enemies[side_index] not in INIMIGOS:
                self.setup_player_enemies[side_index] = next(iter(INIMIGOS))

    def select_setup_relic(self, index, name):
        self.setup_relics[index] = name
        if index == 0:
            self.setup_relic = name

    def set_rival_type(self, side_index, is_enemy):
        self.rival_is_enemy[side_index] = is_enemy
        if is_enemy and self.rival_slots[side_index] not in INIMIGOS:
            self.rival_slots[side_index] = next(iter(INIMIGOS))
        elif not is_enemy and self.rival_slots[side_index] not in CLASSES:
            self.rival_slots[side_index] = next(iter(CLASSES))

    def scroll_enemies(self, direction):
        self.enemy_scroll = max(0, self.enemy_scroll + direction)

    def scroll_classes(self, direction):
        self.class_scroll = max(0, self.class_scroll + direction)

    def scroll_relics(self, direction):
        self.relic_scroll = max(0, self.relic_scroll + direction)

    def start_setup_battle(self):
        self.setup_slot = self.team_size * 2 - 1
        self.next_setup()

    def input_box(self, rect, label, value, focus, hint=""):
        self.text(label, rect[0], rect[1] - 22, MUTED, self.small)
        r = pygame.Rect(rect)
        active = self.setup_focus == focus if focus == "player_name" else self.prompt_field == focus
        pygame.draw.rect(self.screen, (20, 29, 44), r, border_radius=9)
        pygame.draw.rect(self.screen, CYAN if active else (58, 74, 96), r, 1, border_radius=9)
        shown = value or hint
        self.text(shown, r.x + 14, r.y + 12, TEXT if value else MUTED)
        self.buttons.append(Button(r, "", lambda: self.set_input_focus(focus), fill=(0, 0, 0), accent=(0, 0, 0)))

    def set_input_focus(self, focus):
        if focus.startswith("prompt_"):
            self.prompt_field = focus
        else:
            self.setup_focus = focus
            if focus == "player_name":
                pygame.key.start_text_input()

    def select_mode(self, mode):
        self.mode = mode
        self.setup_slot = 0
        self.team_size = {"solo": 1, "dupla": 2}.get(mode, self.team_size)

    def set_team_size(self, size):
        self.team_size, self.setup_slot = size, 0

    def change_slot(self, amount):
        count = (1 if self.mode == "solo" else 2) if self.mode != "multiplayer" else self.team_size * 2
        self.setup_slot = max(0, min(count - 1, self.setup_slot + amount))

    def cycle_setup_class(self, amount):
        options = list(CLASSES)
        if self.mode == "multiplayer" and self.setup_slot >= self.team_size:
            side_index = self.setup_slot - self.team_size
            if self.rival_is_enemy[side_index]:
                options = list(INIMIGOS)
                cur = self.rival_slots[side_index]
                self.rival_slots[side_index] = options[(options.index(cur) + amount) % len(options)] if cur in options else options[0]
            else:
                cur = self.rival_slots[side_index]
                self.rival_slots[side_index] = options[(options.index(cur) + amount) % len(options)]
            return
        cur = self.setup_player_classes[self.setup_slot]
        self.setup_player_classes[self.setup_slot] = options[(options.index(cur) + amount) % len(options)]

    def toggle_rival_type(self):
        slot = self.setup_slot
        if self.mode != "multiplayer" or slot < self.team_size:
            return
        side_index = slot - self.team_size
        self.rival_is_enemy[side_index] = not self.rival_is_enemy[side_index]
        self.rival_slots[side_index] = "morcego" if self.rival_is_enemy[side_index] else "cavaleiro"

    def cycle_relic(self):
        options = ["nenhum", *RELIQUIAS]
        self.setup_relic = options[(options.index(self.setup_relic) + 1) % len(options)]

    def next_setup(self):
        count = (1 if self.mode == "solo" else 2) if self.mode != "multiplayer" else self.team_size * 2
        if self.setup_slot + 1 < count:
            self.change_slot(1)
            return
        players = []
        enemies = []
        if self.mode == "multiplayer":
            for i in range(self.team_size):
                player_name = self.setup_inputs[i].strip() or f"Jogador {i + 1}"
                if self.setup_player_is_enemy[i]:
                    player_kind = self.setup_player_enemies[i]
                    players.append(Fighter.create(player_name, "player", player_kind,
                                                  INIMIGOS[player_kind], self.setup_relics[i]))
                else:
                    players.append(make_player(player_name, self.setup_player_classes[i], self.setup_relics[i]))
                rival_slot = i + 4
                name = self.setup_inputs[rival_slot].strip() or f"Rival {i + 1}"
                if self.rival_is_enemy[i]:
                    source = INIMIGOS[self.rival_slots[i]]
                    enemies.append(Fighter.create(name, "rival", self.rival_slots[i], source, self.setup_relics[rival_slot]))
                else:
                    source = CLASSES[self.rival_slots[i]]
                    enemies.append(Fighter.create(name, "rival", self.rival_slots[i], source, self.setup_relics[rival_slot]))
        else:
            player_count = 1 if self.mode == "solo" else 2
            for i in range(player_count):
                name = self.setup_inputs[i].strip() or f"Jogador {i + 1}"
                players.append(make_player(name, self.setup_player_classes[i], self.setup_relics[i]))
            pool = [name for names in DIFICULDADES.values() for name in names]
            for i in range(player_count):
                name = random.choice(pool)
                if name != "gojo" and random.random() < CHANCE_SECRETO / 100:
                    name = "gojo"
                enemies.append(make_enemy(name))
        self.battle = Battle(players, enemies, self.mode)
        self.inventory = {name: data.get("quantidade", 0) * (2 if self.mode == "dupla" else 1) for name, data in ITENS.items()}
        self.battle.inventory = self.inventory
        self.pending_attack = self.pending_item = None
        self.pending_contract = False
        self.history_scroll = 0
        self.page = "briefing"

    def draw_briefing(self):
        if not self.battle:
            self.go("setup")
            return
        battle = self.battle
        self.header("Antes do combate", "Preparação da batalha", "Confira equipes, clima, terreno e a ordem de ação inicial.")
        self.panel((48, 168, 550, 408), "Equipe A", accent=BLUE)
        self.panel((682, 168, 550, 408), "Equipe B", accent=RED)
        for team, x in ((battle.players, 74), (battle.enemies, 708)):
            y = 228
            for fighter in team:
                self.text_fit(self.fighter_heading(fighter), x, y, 500, TEXT, self.medium)
                self.text(f"HP {fighter.hp}  |  EN {fighter.energy}  |  Velocidade {fighter.speed}  |  Elemento {fighter.element}", x, y + 34, MUTED, self.small)
                y += 82
        self.panel((48, 590, 1184, 92), "Condições", accent=GOLD)
        self.text(f"Clima: {CLIMAS[battle.weather]['nome']}   ·   Terreno: {battle.terrain}", 72, 636, TEXT)
        order = "  →  ".join(self.fighter_heading(f) for f in battle.turn_order)
        self.text_fit("Ordem: " + order, 72, 660, 1128, CYAN, self.small)
        self.add_button((1000, 704, 232, 44), "Começar batalha", self.start_battle, fill=(37, 94, 102))
        self.add_button((48, 704, 190, 44), "Voltar à preparação", lambda: self.go("setup"))

    def start_battle(self):
        self.page = "battle"
        self.advance_automated_turns()

    def draw_battle(self):
        battle = self.battle
        if not battle:
            return
        if battle.winner:
            self.page = "results"
            self.draw_results()
            return
        actor = battle.current
        self.header(f"RODADA {battle.round}   /   MODO {battle.mode.upper()}", "Arena de batalha",
                    f"Clima: {CLIMAS[battle.weather]['nome']}  ·  Terreno: {battle.terrain}  ·  {battle.terrain_turns} rodada(s)")
        self.panel((36, 152, 526, 310), "Equipe A", accent=BLUE)
        self.panel((718, 152, 526, 310), "Equipe B", accent=RED)
        self.draw_team(battle.players, (56, 202, 486, 240), actor)
        self.draw_team(battle.enemies, (738, 202, 486, 240), actor)
        # Indicador de ordem dos turnos
        self.panel((575, 170, 130, 292), "Ordem", accent=GOLD)
        order = battle.turn_order[battle.turn_index:] + battle.turn_order[:battle.turn_index]
        for i, fighter in enumerate(order[:7]):
            self.text_fit(("> " if fighter is actor else "  ") + self.fighter_heading(fighter), 592,
                          218 + i * 32, 96, GOLD if fighter is actor else MUTED, self.small)
        self.panel((36, 480, 772, 238), "Histórico da batalha", accent=CYAN)
        lines = battle.log[-9 - self.history_scroll:len(battle.log) - self.history_scroll if self.history_scroll else None]
        for i, line in enumerate(lines[-8:]):
            self.text_fit("› " + line, 58, 526 + i * 22, 724,
                          TEXT if i == len(lines[-8:]) - 1 else MUTED, self.small)
        self.add_button((650, 486, 48, 34), "▲", lambda: setattr(self, "history_scroll", min(len(battle.log) - 1, self.history_scroll + 1)))
        self.add_button((704, 486, 48, 34), "▼", lambda: setattr(self, "history_scroll", max(0, self.history_scroll - 1)))
        self.panel((830, 480, 414, 238), "Ações", accent=GOLD)
        if actor:
            self.text_fit(f"Turno de {self.fighter_heading(actor)}", 850, 524, 370, GOLD, self.medium)
            if self.pending_attack:
                self.draw_target_actions(actor)
            elif self.pending_item:
                self.draw_item_targets(actor)
            elif self.pending_contract:
                self.draw_contract_options(actor)
            else:
                self.draw_action_buttons(actor)

    def draw_team(self, team, rect, actor):
        x, y, w, h = rect
        for i, fighter in enumerate(team):
            card = pygame.Rect(x, y + i * 116, w, 104)
            active = fighter is actor
            pygame.draw.rect(self.screen, (36, 55, 74) if active else PANEL2, card, border_radius=13)
            pygame.draw.rect(self.screen, GOLD if active else (55, 72, 94), card, 2 if active else 1, border_radius=13)
            avatar_color = BLUE if fighter.side == "player" else RED if fighter.side in ("enemy", "rival") else GOLD
            pygame.draw.circle(self.screen, avatar_color, (card.x + 43, card.y + 50), 26)
            pygame.draw.circle(self.screen, (14, 19, 31), (card.x + 43, card.y + 50), 12)
            name_width = card.w - (252 if fighter.effects else 100)
            self.text_fit(self.fighter_heading(fighter), card.x + 84, card.y + 10, name_width, TEXT, self.font)
            suffix = f"  ·  {fighter.element}" + (f"  ·  {fighter.form}" if fighter.form else "")
            self.text(suffix, card.x + 84, card.y + 34, MUTED, self.small)
            self.bar(card.x + 84, card.y + 58, card.w - 104, 10, fighter.hp, fighter.max_hp, RED)
            self.text(f"HP {fighter.hp}/{fighter.max_hp}     EN {fighter.energy}/{fighter.max_energy}     DEF {fighter.shield}",
                      card.x + 84, card.y + 73, TEXT, self.small)
            if fighter.effects:
                self.text(" · ".join(fighter.effects), card.x + card.w - 154, card.y + 10, GOLD, self.small)

    @staticmethod
    def fighter_heading(fighter):
        character = fighter.kind.replace("_", " ").title()
        if fighter.side == "enemy":
            return f"Robô · {character}"
        return f"{fighter.name} · {character}"

    def bar(self, x, y, w, h, value, maximum, color):
        pygame.draw.rect(self.screen, (12, 17, 27), (x, y, w, h), border_radius=5)
        ratio = max(0, min(1, value / max(1, maximum)))
        pygame.draw.rect(self.screen, color, (x, y, max(3, round(w * ratio)), h), border_radius=5)

    def draw_action_buttons(self, actor):
        labels = [("Atacar", "attack"), ("Defender", "defend"), ("Item", "item"),
                  ("Transformar", "transform"), ("Contrato", "contract"), ("Descansar", "rest"),
                  ("Fugir", "flee"), ("Parar batalha", "quit")]
        for i, (label, action) in enumerate(labels):
            row, col = divmod(i, 2)
            enabled = True
            if action == "contract":
                enabled = bool(CONTRATOS) and not actor.contract and not actor.form and "contrato" not in actor.restrictions
            elif action == "transform":
                enabled = bool(actor.data.get("formas")) and not actor.contract and "transformar" not in actor.restrictions
            self.add_button((850 + col * 183, 570 + row * 40, 172, 34), label,
                            lambda a=action: self.select_action(actor, a),
                            enabled=enabled)

    def draw_contract_options(self, actor):
        contracts = list(CONTRATOS.items())
        for i, (name, data) in enumerate(contracts[:4]):
            row, col = divmod(i, 2)
            x = 850 + col * 183
            y = 568 + row * 56
            self.add_button((x, y, 172, 32), name, lambda n=name: self.choose_contract(actor, n))
            description = data.get("descricao", "")
            benefit = description.split(". Não pode", 1)[0].rstrip(".")
            self.text_fit(benefit, x, y + 34, 172, MUTED, self.small)
        self.add_button((850, 684, 355, 30), "Cancelar", lambda: setattr(self, "pending_contract", False))

    def choose_contract(self, actor, name):
        previous = actor.contract
        self.battle.sign_contract(actor, name)
        self.pending_contract = False
        if actor.contract != previous:
            self.advance_automated_turns()

    def select_action(self, actor, action):
        if action == "attack":
            self.pending_attack = "choose"
            self.attack_page = 0
        elif action == "item":
            self.pending_item = "choose"
        elif action == "defend":
            self.battle.defend(actor)
            self.advance_automated_turns()
        elif action == "rest":
            self.battle.rest(actor)
            self.advance_automated_turns()
        elif action == "flee":
            self.battle.flee(actor)
            self.advance_automated_turns()
        elif action == "quit":
            self.battle.quit_battle(actor)
            self.page = "results"
        elif action == "transform":
            self.battle.transform(actor)
            self.advance_automated_turns()
        elif action == "contract":
            if CONTRATOS and not actor.contract and not actor.form and "contrato" not in actor.restrictions:
                self.pending_contract = True
            else:
                self.battle.sign_contract(actor, next(iter(CONTRATOS), ""))

    def draw_target_actions(self, actor):
        if self.pending_attack == "choose":
            all_attacks = actor.available_attacks()
            page_size = 4
            page_count = max(1, (len(all_attacks) + page_size - 1) // page_size)
            self.attack_page = min(self.attack_page, page_count - 1)
            attacks = all_attacks[self.attack_page * page_size:(self.attack_page + 1) * page_size]
            for i, name in enumerate(attacks):
                data = ATAQUES[name]
                self.add_button((850 + (i % 2) * 183, 568 + (i // 2) * 40, 172, 34),
                                f"{name}  ·  {data.get('energia', 0)} EN", lambda n=name: self.choose_attack(n))
            self.text(f"Página {self.attack_page + 1}/{page_count} · {len(all_attacks)} ataques", 850, 548, MUTED, self.small)
            self.add_button((850, 654, 108, 34), "Anterior", lambda: self.scroll_attacks(-1), enabled=self.attack_page > 0)
            self.add_button((967, 654, 108, 34), "Próxima", lambda: self.scroll_attacks(1), enabled=self.attack_page < page_count - 1)
            self.add_button((1084, 654, 121, 34), "Cancelar", lambda: setattr(self, "pending_attack", None))
        else:
            targets = self.battle.living(self.battle.enemies if actor.side == "player" else self.battle.players)
            for i, target in enumerate(targets[:4]):
                self.add_button((850 + (i % 2) * 183, 568 + (i // 2) * 40, 172, 34), target.name,
                                lambda t=target: self.resolve_attack(actor, t))
            self.add_button((850, 654, 355, 34), "Voltar aos ataques", lambda: setattr(self, "pending_attack", "choose"))

    def choose_attack(self, name):
        actor = self.battle.current
        if not actor:
            return
        if ATAQUES[name].get("area"):
            targets = self.battle.living(self.battle.enemies if actor.side == "player" else self.battle.players)
            self.resolve_attack(actor, targets[0] if targets else actor, name)
        else:
            self.pending_attack, self.pending_item = name, None

    def scroll_attacks(self, direction):
        self.attack_page = max(0, self.attack_page + direction)

    def resolve_attack(self, actor, target, name=None):
        name = name or self.pending_attack
        if name == "choose":
            return
        self.battle.attack(actor, name, target)
        self.pending_attack = None
        self.advance_automated_turns()

    def draw_item_targets(self, actor):
        if self.pending_item == "choose":
            items = [name for name, count in self.inventory.items() if count > 0]
            page_size = 4
            page_count = max(1, (len(items) + page_size - 1) // page_size)
            self.item_page = min(self.item_page, page_count - 1)
            visible = items[self.item_page * page_size:(self.item_page + 1) * page_size]
            for i, name in enumerate(visible):
                self.add_button((850 + (i % 2) * 183, 568 + (i // 2) * 40, 172, 34),
                                f"{name[:16]} ×{self.inventory[name]}", lambda n=name: self.choose_item(n))
            self.text(f"Página {self.item_page + 1}/{page_count} · todos os itens disponíveis", 850, 548, MUTED, self.small)
            self.add_button((850, 654, 108, 34), "Anterior", lambda: self.scroll_items(-1), enabled=self.item_page > 0)
            self.add_button((967, 654, 108, 34), "Próxima", lambda: self.scroll_items(1), enabled=self.item_page < page_count - 1)
            self.add_button((1084, 654, 121, 34), "Cancelar", lambda: setattr(self, "pending_item", None))
        else:
            item_kind = ITENS.get(self.pending_item, {}).get("tipo")
            ally_item = item_kind in {"cura", "energia", "antidoto", "ressusitador", "forca", "aleatorio", "velocidade", "tipagem", "maximizadora"}
            target_own_team = ally_item
            if item_kind in {"fumaca", "negacao"}:
                target_own_team = True
            if item_kind in {"bomba", "pedra", "climatica", "vulnerabilidade"}:
                target_own_team = False
            own_team = self.battle.players if actor.side == "player" else self.battle.enemies
            enemy_team = self.battle.enemies if actor.side == "player" else self.battle.players
            eligible = self.battle.living(own_team if target_own_team else enemy_team)
            for i, target in enumerate(eligible[:4]):
                self.add_button((850 + (i % 2) * 183, 568 + (i // 2) * 40, 172, 34), target.name,
                                lambda t=target: self.resolve_item(actor, t))
            self.add_button((850, 654, 355, 34), "Cancelar", lambda: setattr(self, "pending_item", None))

    def choose_item(self, name):
        self.pending_item = name

    def scroll_items(self, direction):
        self.item_page = max(0, self.item_page + direction)

    def resolve_item(self, actor, target):
        self.battle.use_item(actor, self.pending_item, target, self.inventory)
        self.pending_item = None
        self.advance_automated_turns()

    def advance_automated_turns(self):
        if not self.battle or self.battle.winner:
            return
        while (self.battle.current and self.battle.current.side not in ("player", "rival")):
            actor = self.battle.current
            self.battle.ai_action(actor)
            if self.battle.winner:
                break
        if self.battle.winner:
            self.page = "results"

    def draw_results(self):
        if not self.battle:
            return
        winner = self.battle.winner
        title = {"player": "Vitória!", "enemy": "Derrota", "escape": "Batalha encerrada", "quit": "Batalha interrompida"}.get(winner, "Batalha encerrada")
        self.text("RESULTADO DA BATALHA", 62, 60, CYAN, self.medium)
        self.text(title, 60, 104, TEXT, self.large)
        subtitle = "Seu grupo venceu." if winner == "player" else "Todos os combatentes do grupo foram derrotados." if winner == "enemy" else "Você encerrou a batalha." if winner == "quit" else "Seu grupo fugiu da batalha."
        self.text(subtitle, 64, 164, MUTED)
        self.panel((62, 230, 540, 350), "Estatísticas")
        self.text(f"Turnos: {self.battle.round}", 90, 292, TEXT)
        self.text(f"Clima final: {CLIMAS[self.battle.weather]['nome']}", 90, 328, TEXT)
        self.text("Dano causado", 90, 382, CYAN, self.medium)
        y = 422
        for name, value in self.battle.damage_dealt.items():
            self.text(f"{name}: {value}", 96, y, TEXT, self.small); y += 24
        self.text("Dano recebido", 324, 382, GOLD, self.medium)
        y = 422
        for name, value in self.battle.damage_received.items():
            self.text(f"{name}: {value}", 330, y, TEXT, self.small); y += 24
        self.add_button((64, 624, 230, 52), "Nova batalha", lambda: self.go_setup(), fill=(37, 94, 102))
        self.add_button((312, 624, 230, 52), "Menu principal", lambda: self.go("home"))

    def draw_dev(self):
        self.header("Dev Tools", "Ambiente de teste", "Console de comandos e Dummy de 5000 HP para exercitar as regras do combate.")
        if not self.dev_dummy:
            self.dev_dummy = Fighter.create("Dummy", "enemy", "dummy", {"vida": 5000, "energia": 0, "velocidade": 1, "defesa": 0, "critico": 0})
        if not self.dev_battle:
            tester = Fighter.create("Testador", "player", "cavaleiro", CLASSES["cavaleiro"])
            self.dev_battle = Battle([tester], [self.dev_dummy], "dev")
        self.panel((42, 162, 370, 488), "Dummy", accent=GOLD)
        self.text(f"HP   {self.dev_dummy.hp}/{self.dev_dummy.max_hp}", 70, 222, TEXT, self.medium)
        self.bar(70, 264, 300, 16, self.dev_dummy.hp, self.dev_dummy.max_hp, GREEN)
        self.text(f"Energia {self.dev_dummy.energy}   Defesa 0   Velocidade 1   Crítico 0", 70, 298, MUTED, self.small)
        self.text("Efeitos ativos", 70, 350, CYAN, self.font)
        self.text(", ".join(self.dev_dummy.effects) or "Nenhum", 70, 380, TEXT)
        self.text("Terreno", 70, 430, CYAN, self.font)
        self.text(self.dev_battle.terrain if self.dev_battle else "Campo comum", 70, 458, TEXT)
        self.add_button((70, 544, 290, 42), "Reiniciar Dummy", self.reset_dummy)
        self.panel((338, 162, 580, 488), "Comandos", accent=CYAN)
        self.text("Digite um comando e pressione Enter:", 362, 220, MUTED, self.small)
        pygame.draw.rect(self.screen, (15, 22, 35), (360, 247, 536, 48), border_radius=9)
        pygame.draw.rect(self.screen, CYAN, (360, 247, 536, 48), 1, border_radius=9)
        self.text(self.dev_input or "@apply_burn", 376, 261, TEXT if self.dev_input else MUTED)
        log_y = 316
        for line in self.dev_log[-11:]:
            self.text(line[:72], 364, log_y, MUTED, self.small); log_y += 25
        if self.dev_waiting_confirmation:
            self.add_button((360, 588, 250, 40), "Funcionou", lambda: self.record_dev_result(True), fill=(38, 91, 69), accent=GREEN)
            self.add_button((632, 588, 250, 40), "Não funcionou", lambda: self.record_dev_result(False), accent=RED)
        self.panel((942, 162, 296, 488), "Resultados", accent=GOLD)
        self.text(f"FUNCIONANDO · {len(self.dev_working)}", 964, 220, GREEN, self.font)
        self.paragraph(", ".join(self.dev_working[-7:]) or "Ainda sem registros", 964, 252, 248, MUTED, self.small)
        self.text(f"NÃO FUNCIONANDO · {len(self.dev_failing)}", 964, 396, RED, self.font)
        self.paragraph(", ".join(self.dev_failing[-7:]) or "Ainda sem registros", 964, 428, 248, MUTED, self.small)
        self.add_button((42, 680, 190, 44), "← Configurações", lambda: self.go("settings"))

    @property
    def dev_log(self):
        if not hasattr(self, "_dev_log"):
            self._dev_log = ["Aguardando comando de teste."]
        return self._dev_log

    def reset_dummy(self):
        self.dev_dummy = Fighter.create("Dummy", "enemy", "dummy", {"vida": 5000, "energia": 0, "velocidade": 1, "defesa": 0, "critico": 0})
        tester = Fighter.create("Testador", "player", "cavaleiro", CLASSES["cavaleiro"])
        self.dev_battle = Battle([tester], [self.dev_dummy], "dev")
        self.notify("Dummy reiniciado.")

    def run_dev_command(self):
        command = self.dev_input.strip()
        if not command:
            return
        normalized = command.lower()
        aliases = {"@apply_freezy": "congelado", "@apply_shock": "paralisado", "@apply_burn": "queima",
                   "@apply_slow": "lento", "@apply_toxic": "veneno", "@apply_blooding": "sangramento",
                   "@apply_scary": "medo"}
        if normalized.startswith("@apply_effect in "):
            effect = normalized.split(" in ", 1)[1].strip(" ()")
            effect = {"freezy": "congelado", "shock": "paralisado", "burn": "queima", "slow": "lento",
                      "toxic": "veneno", "blooding": "sangramento", "scary": "medo"}.get(effect, effect)
            if effect in ("efeitos", "todos", "all"):
                for status in EFEITOS:
                    self.dev_battle.apply_effect(self.dev_dummy, status, 3)
            else:
                self.dev_battle.apply_effect(self.dev_dummy, effect, 3)
        elif normalized in aliases:
            self.dev_battle.apply_effect(self.dev_dummy, aliases[normalized], 3)
        elif normalized.startswith("@apply_elemente_terrain in "):
            terrain = command.split(" in ", 1)[1].strip(" ()")
            self.dev_battle.set_terrain(terrain)
        elif normalized.startswith(("@applt_combination in @n ", "@apply_combination in @n ")):
            combination = command.split("@n ", 1)[1].strip(" ()")
            self.dev_battle.apply_combination(combination)
        elif normalized == "@apply_hit_kill in dummy":
            self.dev_dummy.hp = 0
            self.dev_dummy.alive = False
            self.dev_log.append("Dummy eliminado instantaneamente.")
        elif normalized.startswith("@apply_transform in @n "):
            values = [part.strip(" ()") for part in command.split("@n ", 1)[-1].split(",") if part.strip(" (),")]
            target_name = next((v.casefold() for v in values if v.casefold() in INIMIGOS or v.casefold() in CLASSES), None)
            if target_name in INIMIGOS:
                self.dev_dummy.kind, self.dev_dummy.data = target_name, dict(INIMIGOS[target_name])
                self.dev_dummy.form = None
                self.dev_log.append(f"Dummy transformado em {target_name}.")
            elif target_name in CLASSES:
                self.dev_dummy.kind, self.dev_dummy.data = target_name, dict(CLASSES[target_name])
                self.dev_dummy.form = None
                self.dev_log.append(f"Dummy transformado na classe {target_name}.")
            else:
                self.dev_dummy.form = values[-1] if values else "Forma de teste"
                self.dev_log.append(f"Transformação de teste: {self.dev_dummy.form}.")
        else:
            self.dev_log.append(f"Comando desconhecido: {command}")
            self.dev_waiting_confirmation = command
            self.dev_input = ""
            return
        self.dev_log.extend(self.dev_battle.log[-1:])
        self.dev_waiting_confirmation = command
        self.dev_input = ""

    def record_dev_result(self, worked):
        target = self.dev_working if worked else self.dev_failing
        target.append(self.dev_waiting_confirmation)
        self.save_dev_results()
        self.dev_log.append("Resultado guardado: " + ("funcionando" if worked else "não funcionando"))
        self.dev_waiting_confirmation = None

    def draw_prompts(self):
        self.header("Ateliê", "Preparação de imagens", "Organize descrições e prompts; a geração das imagens acontece fora do jogo.")
        self.panel((48, 164, 560, 470), "Briefing", accent=GOLD)
        self.text("Categoria", 74, 222, MUTED, self.small)
        self.add_button((72, 250, 236, 46), f"Categoria: {self.prompt_category}", self.cycle_prompt_category)
        self.text("Nome / assunto", 74, 322, MUTED, self.small)
        self.input_box((72, 346, 496, 44), "", self.prompt_name, "prompt_name")
        self.text("Descrição visual", 74, 420, MUTED, self.small)
        self.input_box((72, 444, 496, 44), "", self.prompt_description, "prompt_description", hint="Estilo, cores, pose, cenário...")
        self.add_button((72, 524, 240, 48), "Preparar prompt", self.generate_prompt, fill=(37, 94, 102))
        self.panel((636, 164, 596, 470), "Prompt pronto", accent=CYAN)
        self.paragraph(self.prompt_result or "Exemplo de uso: selecione Personagem, dê um nome e descreva estilo, ângulo, expressão e iluminação.", 664, 224, 536, TEXT, self.font)
        self.add_button((48, 680, 190, 44), "← Configurações", lambda: self.go("settings"))

    def cycle_prompt_category(self):
        options = ["Personagem", "Inimigo", "Cenário", "Terreno", "Clima", "Item", "Relíquia", "Ataque", "Efeito", "Mega Forma", "Ícone", "Interface"]
        self.prompt_category = options[(options.index(self.prompt_category) + 1) % len(options)]

    def generate_prompt(self):
        subject = self.prompt_name or self.prompt_category
        details = self.prompt_description or "fantasia original, acabamento pintado, silhueta legível e paleta rica"
        view = "retrato frontal e ícone de rosto; pose de ataque dinâmica; vista traseira para a tela de batalha" if self.prompt_category in ("Personagem", "Inimigo") else "composição clara, silhueta reconhecível, sem texto e com fundo utilizável em jogo"
        self.prompt_result = f"Arte original para RPG de fantasia: {subject}. {details}. {view}. Paleta consistente com o elemento e iluminação cinematográfica suave. Não imitar personagens nem interfaces de franquias existentes."
        path = ROOT / "image_prompt_catalog.json"
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            entries = []
        entries.append({"categoria": self.prompt_category, "nome": subject, "descricao": details, "prompt": self.prompt_result})
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        self.notify("Prompt guardado em image_prompt_catalog.json.")

    def go(self, page):
        self.page = page

    def click(self, pos):
        for button in reversed(self.buttons):
            if button.hit(pos):
                button.action()
                return

    def handle_key(self, event):
        if self.page == "settings" and self.dev_auth_stage:
            if event.key == pygame.K_ESCAPE:
                self.dev_auth_stage = None
                self.dev_auth_input = ""
            elif event.key == pygame.K_RETURN:
                self.submit_dev_auth()
            elif event.key == pygame.K_BACKSPACE:
                self.dev_auth_input = self.dev_auth_input[:-1]
            elif event.unicode.isprintable() and len(self.dev_auth_input) < 64:
                self.dev_auth_input += event.unicode
            return
        if event.key == pygame.K_ESCAPE:
            if self.page == "battle":
                self.notify("Use a ação Fugir para encerrar a batalha.")
            elif self.page in ("settings", "setup", "dev", "prompts", "results"):
                self.go("home")
            return
        if self.page == "setup" and self.setup_focus == "player_name":
            i = self.setup_name_index
            value = self.setup_inputs[i]
            if event.key == pygame.K_BACKSPACE:
                self.setup_inputs[i] = value[:-1]
            elif event.key == pygame.K_RETURN:
                self.setup_focus = ""
            elif event.unicode.isprintable() and len(value) < 22:
                self.setup_inputs[i] += event.unicode
        elif self.page == "dev":
            if event.key == pygame.K_RETURN:
                self.run_dev_command()
            elif event.key == pygame.K_BACKSPACE:
                self.dev_input = self.dev_input[:-1]
            elif event.unicode.isprintable() and len(self.dev_input) < 100:
                self.dev_input += event.unicode
        elif self.page == "prompts":
            target = self.prompt_field
            value = getattr(self, target)
            if event.key == pygame.K_TAB:
                self.prompt_field = "prompt_description" if target == "prompt_name" else "prompt_name"
            elif event.key == pygame.K_BACKSPACE:
                setattr(self, target, value[:-1])
            elif event.unicode.isprintable() and len(value) < 180:
                setattr(self, target, value + event.unicode)

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.click(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 4 and self.page == "battle":
                    self.history_scroll = min(len(self.battle.log), self.history_scroll + 2)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5 and self.page == "battle":
                    self.history_scroll = max(0, self.history_scroll - 2)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
            self.draw()
            self.clock.tick(60)
        pygame.quit()


def run():
    RPGApp().run()
