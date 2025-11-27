import pygame
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpeechCommand:
    """Describes a speech animation request for the coach bird."""
    duration: float = 2.0  # seconds the beak animation should play
    text: Optional[str] = None  # placeholder for future text support


class CoachBirdAgent:
    """Lightweight companion bird rendered in a bottom panel.

    The agent supports a celebratory bounce and a simple beak animation to
    indicate speech. The beak animation is intentionally simple so that a
    downstream LLM + TTS pipeline can trigger it while audio plays.
    """

    def __init__(self, screen_width: int, screen_height: int, panel_height: int = 110):
        self.panel_padding = 10
        self.panel_height = panel_height
        self.panel_rect = pygame.Rect(
            self.panel_padding,
            screen_height - panel_height - self.panel_padding,
            screen_width - self.panel_padding * 2,
            panel_height,
        )

        # Load two frames to toggle the beak while "speaking".
        self.idle_frame = pygame.image.load("assets/sprites/bluebird-midflap.png").convert_alpha()
        self.beak_frame = pygame.image.load("assets/sprites/bluebird-downflap.png").convert_alpha()
        self.shadow = pygame.Surface((self.idle_frame.get_width(), 6), pygame.SRCALPHA)
        self.shadow.fill((0, 0, 0, 70))

        self.speaking: bool = False
        self.speech_end_time: int = 0
        self.last_beak_switch: int = 0
        self.beak_interval_ms: int = 150
        self.display_text: Optional[str] = None
        self.label_font = pygame.font.SysFont("Impact", 18)
        self.dialog_box = PixelDialogBox(width=self.panel_rect.width - 32)

        # Simple bounce physics for the high-score celebration.
        self.jump_offset: float = 0.0
        self.jump_velocity: float = 0.0
        self.jump_gravity: float = 900.0

        # Panel appearance.
        self.panel_surface = pygame.Surface((self.panel_rect.width, self.panel_rect.height), pygame.SRCALPHA)
        self.panel_color = (18, 18, 28, 210)
        self.border_color = (240, 234, 161)

    def trigger_high_score_bounce(self) -> None:
        """Kick off a short upward bounce to acknowledge a new high score."""
        if self.jump_offset == 0.0:
            self.jump_velocity = -220.0

    def start_speaking(self, command: SpeechCommand) -> None:
        """Begin a simple beak animation for the provided duration."""
        now = pygame.time.get_ticks()
        self.speaking = True
        self.speech_end_time = now + int(command.duration * 1000)
        self.last_beak_switch = now
        self.display_text = command.text

    def stop_speaking(self) -> None:
        self.speaking = False
        self.display_text = None

    def update(self, delta_time: float) -> None:
        """Advance bounce physics and speech timing."""
        now = pygame.time.get_ticks()

        if self.speaking and now >= self.speech_end_time:
            self.stop_speaking()

        # Bounce physics.
        if self.jump_velocity != 0.0 or self.jump_offset != 0.0:
            self.jump_velocity += self.jump_gravity * delta_time
            self.jump_offset += self.jump_velocity * delta_time
            if self.jump_offset > 0:
                self.jump_offset = 0
                self.jump_velocity = 0

        self.dialog_box.update(now)

        # Toggle beak while speaking.
        if self.speaking and now - self.last_beak_switch >= self.beak_interval_ms:
            self.last_beak_switch = now

    def _current_frame(self) -> pygame.Surface:
        if self.speaking and (pygame.time.get_ticks() // self.beak_interval_ms) % 2 == 0:
            return self.beak_frame
        return self.idle_frame

    def draw(self, surface: pygame.Surface) -> None:
        # Draw panel background.
        self.panel_surface.fill(self.panel_color)
        pygame.draw.rect(self.panel_surface, self.border_color, self.panel_surface.get_rect(), width=2)

        # Draw the bird sprite with bounce and a subtle shadow.
        bird_frame = self._current_frame()
        sprite_x = 20
        sprite_y = (self.panel_rect.height // 2) - (bird_frame.get_height() // 2) + int(self.jump_offset)
        shadow_y = sprite_y + bird_frame.get_height() - 6
        self.panel_surface.blit(self.shadow, (sprite_x + 2, shadow_y))
        self.panel_surface.blit(bird_frame, (sprite_x, sprite_y))

        # Optional speech label for future TTS/LLM output.
        if self.display_text:
            text_surface = self.label_font.render(self.display_text, True, (240, 234, 161))
            self.panel_surface.blit(text_surface, (sprite_x + bird_frame.get_width() + 12, sprite_y + 10))

        # Draw dialog text box with Undertale-inspired pixel edges.
        if self.dialog_box.is_visible:
            dialog_rect = pygame.Rect(
                sprite_x + bird_frame.get_width() + 16,
                10,
                self.panel_rect.width - sprite_x - bird_frame.get_width() - 30,
                self.panel_rect.height - 20,
            )
            self.dialog_box.draw(self.panel_surface, dialog_rect)

        # Render active state labels even when no text is provided.
        status = """Thinking...""" if self.speaking else "Ready"
        status_surface = self.label_font.render(status, True, (240, 234, 161))
        self.panel_surface.blit(status_surface, (self.panel_rect.width - status_surface.get_width() - 14, self.panel_rect.height - status_surface.get_height() - 10))

        surface.blit(self.panel_surface, self.panel_rect.topleft)

    @property
    def is_speaking(self) -> bool:
        return self.speaking

    def show_dialog(self, text: str, duration: float = 4.0) -> None:
        """Display a pixelated dialog box with wrapped text for a limited time."""
        self.dialog_box.show(text, duration)


class PixelDialogBox:
    """Utility to render Undertale-like pixelated dialog text within a panel."""

    def __init__(self, width: int):
        matched_font = pygame.font.match_font(
            "pressstart2p,vt323,perfectdosvga437,consolas,couriernew,menlo,monospace"
        )
        # Use a slightly larger monospace font to avoid post-render scaling blur.
        self.font = pygame.font.Font(matched_font or None, 16)
        self.padding = 12
        self.width = width - self.padding * 2
        self.text_color = (248, 248, 248)
        self.text_outline_color = (24, 24, 24)
        self.box_color = (0, 0, 0, 210)
        self.border_color = (240, 234, 161)
        self.line_spacing = 4
        self.visible_until: Optional[int] = None
        self.lines: list[str] = []

    @property
    def is_visible(self) -> bool:
        return self.visible_until is not None

    def show(self, text: str, duration: float) -> None:
        self.lines = self._wrap_text(text)
        self.visible_until = pygame.time.get_ticks() + int(duration * 1000)

    def update(self, now_ms: int) -> None:
        if self.visible_until is not None and now_ms >= self.visible_until:
            self.visible_until = None
            self.lines = []

    def draw(self, surface: pygame.Surface, target_rect: pygame.Rect) -> None:
        if not self.is_visible:
            return

        dialog_surface = pygame.Surface(target_rect.size, pygame.SRCALPHA)
        dialog_surface.fill(self.box_color)
        pygame.draw.rect(dialog_surface, self.border_color, dialog_surface.get_rect(), width=2)

        y = self.padding
        for line in self.lines:
            rendered = self._render_text(line)
            dialog_surface.blit(rendered, (self.padding, y))
            y += rendered.get_height() + self.line_spacing

        surface.blit(dialog_surface, target_rect.topleft)

    def _wrap_text(self, text: str) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current_line: list[str] = []

        for word in words:
            prospective = " ".join(current_line + [word]) if current_line else word
            width, _ = self.font.size(prospective)
            if width <= self.width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def _render_text(self, text: str) -> pygame.Surface:
        """Render text with a 1px outline for readability."""
        text_surface = self.font.render(text, False, self.text_color)
        outline_surface = pygame.Surface(
            (text_surface.get_width() + 2, text_surface.get_height() + 2), pygame.SRCALPHA
        )
        outline_offsets = ((0, 1), (2, 1), (1, 0), (1, 2))
        for ox, oy in outline_offsets:
            outline_surface.blit(
                self.font.render(text, False, self.text_outline_color), (ox, oy)
            )
        outline_surface.blit(text_surface, (1, 1))
        return outline_surface
