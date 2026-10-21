"""Title screen for Fly-in.

Renders the animated title/menu screen (background grid, decorative
mini path preview, title text, and menu buttons) and blocks until the
player picks a menu entry or closes the window.

This module reuses the shared ``Colors``, ``Renderer``, ``Button`` and
``MiniPath`` building blocks from :mod:`ui_clean` instead of
redefining them, to avoid duplicating the same drawing primitives in
two places.
"""

import math
from typing import Dict, Optional

from pyray import (
    MouseButton,
    Vector2,
    begin_drawing,
    clear_background,
    draw_line,
    draw_line_ex,
    draw_text,
    end_drawing,
    get_frame_time,
    get_mouse_position,
    get_screen_height,
    get_screen_width,
    get_time,
    is_mouse_button_pressed,
    window_should_close,
)

from ui import Button as Button
from ui import Colors as Colors
from ui import MiniPath as MiniPath
from ui import Renderer as Renderer


def run_title_screen(
    has_save: bool = False,
    title: str = "FLY-IN",
    subtitle: str = "ESTHETIQUE DARK / NEON",
) -> Optional[str]:
    """Run the title screen loop until a menu choice or window close.

    Args:
        has_save: Whether a save file exists, enabling the
            "continue" and "parametres" menu entries.
        title: Main title text.
        subtitle: Subtitle text shown below the title.

    Returns:
        The key of the button the player clicked (``"new game"``,
        ``"continue"``, ``"paramettres"`` or ``"settings"``), or
        ``None`` if the window was closed without a selection.
    """
    screen_w = get_screen_width()
    screen_h = get_screen_height()

    panel_w = max(380, int(screen_w * 0.32))
    btn_w = min(300, panel_w - 80)
    btn_h = 50
    gap = 14
    btn_x = (panel_w - btn_w) // 2

    total_ui_h = 110 + (3 * btn_h + 2 * gap)
    start_y = max(60, (screen_h - total_ui_h) // 2)

    title_y = start_y
    buttons_y = title_y + 110

    preview_x = panel_w + 40
    preview_y = int(screen_h * 0.12)
    preview_w = screen_w - preview_x - 60
    preview_h = int(screen_h * 0.76)

    preview = MiniPath(preview_x, preview_y, preview_w, preview_h)

    buttons: Dict[str, Button] = {
        "new game": Button("NEW GAME", btn_x, buttons_y, btn_w, btn_h),
        "continue": Button(
            "CONTINUER",
            btn_x,
            buttons_y + 1 * (btn_h + gap),
            btn_w,
            btn_h,
            enabled=has_save,
        ),
        "paramettres": Button(
            "PARAMETTRES",
            btn_x,
            buttons_y + 2 * (btn_h + gap),
            btn_w,
            btn_h,
            enabled=has_save,
        ),
        "settings": Button(
            "QUIT",
            btn_x,
            buttons_y + 3 * (btn_h + gap),
            btn_w,
            btn_h,
        ),
    }

    t0 = get_time()

    while not window_should_close():
        dt = get_frame_time()
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)
        elapsed = get_time() - t0

        preview.update(dt)

        for key, btn in buttons.items():
            if btn.update(mouse, pressed, dt):
                return key

        begin_drawing()
        clear_background(Colors.BG)

        for gx in range(0, screen_w, 40):
            draw_line(gx, 0, gx, screen_h, Colors.GRID)
        for gy in range(0, screen_h, 40):
            draw_line(0, gy, screen_w, gy, Colors.GRID)

        draw_line_ex(
            Vector2(panel_w, 40),
            Vector2(panel_w, screen_h - 40),
            1.0,
            Renderer.with_alpha(Colors.TEXT, 14),
        )

        preview.draw()

        title_size = 40
        Renderer.draw_text_spaced(
            title, btn_x, title_y, title_size, Colors.TEXT, 5
        )
        sub_size = 11
        Renderer.draw_text_spaced(
            subtitle,
            btn_x + 2,
            title_y + title_size + 12,
            sub_size,
            Renderer.with_alpha(Colors.MUTED, 220),
            3,
        )

        breathe = 1.0 + math.sin(elapsed * 1.4) * 0.08
        Renderer.glow_ring(
            btn_x + 6, title_y - 14, 3 * breathe, 1.2, Colors.PATH, 200
        )

        for btn in buttons.values():
            btn.draw()

        foot = "15 drones | 26 circuits | map: ultimate_challenge"
        draw_text(
            foot,
            btn_x,
            screen_h - 46,
            11,
            Renderer.with_alpha(Colors.MUTED, 150),
        )

        end_drawing()

    return None
