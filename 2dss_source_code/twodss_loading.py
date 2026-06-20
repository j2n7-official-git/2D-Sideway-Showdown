"""
TWODSS_LOADING.PY - Màn hình chờ (Loading Bar) trước khi đua
"""
import pygame
import os
import random

class LoadingScreen:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.progress = 0.0
        self.is_done = False

        # Load vài hình nền random cho ngầu
        bg_dir = os.path.join(base_dir, "assets", "background_game")
        self.bg_images = []
        try:
            for img_name in ["2dss_intro.PNG", "2dss_standby_bg.PNG", "showroom-car-select.png"]:
                path = os.path.join(bg_dir, img_name)
                if os.path.exists(path):
                    self.bg_images.append(pygame.image.load(path).convert())
        except:
            pass
        self.current_bg = None

        pygame.font.init()
        self.font = pygame.font.SysFont("impact", 40)

    def reset(self):
        """Được gọi từ core_main trước khi vào màn đua mới"""
        self.progress = 0.0
        self.is_done = False
        if self.bg_images:
            self.current_bg = random.choice(self.bg_images)
            self.current_bg = pygame.transform.scale(self.current_bg, (1920, 1080))

    def update(self, dt):
        # Giả lập load bar chạy trong 2.5 giây
        self.progress += (dt / 2500.0)
        if self.progress >= 1.0:
            self.progress = 1.0
            self.is_done = True

    def draw(self, screen):
        if self.current_bg:
            screen.blit(self.current_bg, (0, 0))
        else:
            screen.fill((15, 15, 20))

        # Phủ lớp mờ cho dễ nhìn chữ
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Vẽ thanh Loading
        sw, sh = screen.get_size()
        bar_w, bar_h = 800, 40
        bx = (sw - bar_w) // 2
        by = sh - 150

        # Khung viền thanh load
        pygame.draw.rect(screen, (255, 255, 255), (bx-2, by-2, bar_w+4, bar_h+4), 2)
        # Lõi thanh load màu cam gradient
        pygame.draw.rect(screen, (255, 140, 0), (bx, by, int(bar_w * self.progress), bar_h))

        # Chữ LOADING
        txt = self.font.render(f"LOADING MAP... {int(self.progress * 100)}%", True, (255, 255, 255))
        screen.blit(txt, (bx, by - 50))