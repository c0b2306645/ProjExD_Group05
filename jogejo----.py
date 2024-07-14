#!/usr/bin/env python
import os
import random
from typing import List

import pygame as pg

if not pg.image.get_extended():
    raise SystemExit("Sorry, extended image module required")

# Game Constants
MAX_SHOTS = 1
MAX_BOMBS = 1
SCREENRECT = pg.Rect(0, 0, 640, 480)
SCORE = 0
main_dir = os.path.split(os.path.abspath(__file__))[0]


def load_image(file):
    """loads an image, prepares it for play"""
    file = os.path.join(main_dir, "data", file)
    try:
        surface = pg.image.load(file)
    except pg.error:
        raise SystemExit(f'Could not load image "{file}" {pg.get_error()}')
    return surface.convert()


def load_sound(file):
    """because pygame can be compiled without mixer."""
    if not pg.mixer:
        return None
    file = os.path.join(main_dir, "data", file)
    try:
        sound = pg.mixer.Sound(file)
        return sound
    except pg.error:
        print(f"Warning, unable to load, {file}")
    return None


class Gauge(pg.sprite.Sprite):
    """
    ゲージを管理して表示するクラス
    """

    def __init__(self, position, *groups):
        super().__init__(*groups)
        self.image = pg.Surface((30, 100))
        self.image.fill((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.topleft = position
        self.capacity = 10  # ゲージの最大容量
        self.current_value = 0  # 現在のゲージの量
        self.fill_color = (0, 255, 0)  # ゲージの満タン時の色
        self.empty_color = (255, 0, 0)  # ゲージの空の時の色
        self.last_update = pg.time.get_ticks()  # 前回ゲージが更新された時間
        self.font = pg.font.Font(None, 20)  # 数字表示用のフォント

    def update(self):
        """
        ゲージの値に応じて描画を更新する
        """
        # 現在のゲージの量に応じて、ゲージの長さを計算する
        gauge_length = int(self.current_value / self.capacity * self.rect.height)
        fill_rect = pg.Rect(0, self.rect.height - gauge_length, self.rect.width, gauge_length)
        # ゲージを描画する
        self.image.fill(self.empty_color)
        pg.draw.rect(self.image, self.fill_color, fill_rect)
        # 数字でゲージの量を表示する
        text = self.font.render(str(self.current_value), True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        self.image.blit(text, text_rect)

    def increase(self):
        """
        2秒ごとにゲージを2増やす
        """
        now = pg.time.get_ticks()
        if now - self.last_update > 2000:  # 2秒経過したら
            self.last_update = now
            self.current_value += 1
            if self.current_value > self.capacity:
                self.current_value = self.capacity

    def can_fire(self):
        """
        ゲージが2以上なら発射可能
        """
        return self.current_value >= 2


class Player(pg.sprite.Sprite):
    """
    Playerのクラス
    """

    speed = 5
    gun_offset = 0
    images: List[pg.Surface] = []

    def __init__(self, *groups):
        super().__init__(*groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=SCREENRECT.midbottom)
        self.reloading = 0
        self.origtop = self.rect.top
        self.facing = -1
        self.gauge = Gauge((10, SCREENRECT.height - 100), *groups)  # プレイヤーのゲージ

    def move(self, direction):
        if direction:
            self.facing = direction
        self.rect.move_ip(direction * self.speed, 0)
        self.rect = self.rect.clamp(SCREENRECT)
        if direction < 0:
            self.image = self.images[0]
        elif direction > 0:
            self.image = self.images[1]

    def gunpos(self):
        pos = self.facing * self.gun_offset + self.rect.centerx
        return pos, self.rect.top


class Alien(pg.sprite.Sprite):
    """
    Alienのクラス
    """

    speed = 5
    gun_offset = 0
    images: List[pg.Surface] = []

    def __init__(self, *groups):
        super().__init__(*groups)
        self.image = self.images[0]
        self.reloading = 0
        self.rect = self.image.get_rect(midtop=SCREENRECT.midtop)
        self.facing = -1
        self.origbottom = self.rect.bottom
        self.gauge = Gauge((10, 10), *groups)  # エイリアンのゲージ

    def move(self, direction):
        if direction:
            self.facing = direction
        self.rect.move_ip(direction * self.speed, 0)
        self.rect = self.rect.clamp(SCREENRECT)
        if direction < 0:
            self.image = self.images[0]
        elif direction > 0:
            self.image = self.images[1]

    def gunpos(self):
        pos = self.rect.centerx
        return pos, self.rect.bottom

    def update(self):
        if not SCREENRECT.contains(self.rect):
            self.facing = -self.facing
            self.rect = self.rect.clamp(SCREENRECT)


class Explosion(pg.sprite.Sprite):
    """
    Explosion effect when objects collide
    """

    defaultlife = 12
    animcycle = 3
    images: List[pg.Surface] = []

    def __init__(self, actor, *groups):
        super().__init__(*groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(center=actor.rect.center)
        self.life = self.defaultlife

    def update(self):
        self.life -= 1
        self.image = self.images[self.life // self.animcycle % 2]
        if self.life <= 0:
            self.kill()


class Shot(pg.sprite.Sprite):
    """
    Player's shot class
    """

    speed = -10
    images: List[pg.Surface] = []

    def __init__(self, pos, *groups):
        super().__init__(*groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=pos)

    def update(self):
        self.rect.move_ip(0, self.speed)
        if self.rect.top <= 0:
            self.kill()


class Bomb(pg.sprite.Sprite):
    """
    Alien's bomb class
    """

    speed = 10
    images: List[pg.Surface] = []

    def __init__(self, alien_pos, *groups):
        super().__init__(*groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midtop=alien_pos)

    def update(self):
        self.rect.move_ip(0, self.speed)
        if self.rect.bottom >= SCREENRECT.bottom:
            self.kill()


class Score(pg.sprite.Sprite):
    """
    Score display class
    """

    def __init__(self, *groups):
        super().__init__(*groups)
        self.font = pg.font.Font(None, 20)
        self.font.set_italic(1)
        self.color = "white"
        self.lastscore = -1
        self.update()
        self.rect = self.image.get_rect().move(10, 450)

    def update(self):
        if SCORE != self.lastscore:
            self.lastscore = SCORE
            msg = f"Score: {SCORE}"
            self.image = self.font.render(msg, 0, self.color)


def main(winstyle=0):
    if pg.get_sdl_version()[0] == 2:
        pg.mixer.pre_init(44100, 32, 2, 1024)
    pg.init()
    if pg.mixer and not pg.mixer.get_init():
        print("Warning, no sound")
        pg.mixer = None

    fullscreen = False
    winstyle = 0
    bestdepth = pg.display.mode_ok(SCREENRECT.size, winstyle, 32)
    screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)

    img = load_image("3.png")
    Player.images = [img, pg.transform.flip(img, 1, 0)]
    img = load_image("explosion1.gif")
    Explosion.images = [img, pg.transform.flip(img, 1, 1)]
    Alien.images = [load_image(im) for im in ("alien1.gif", "alien2.gif", "alien3.gif")]
    Bomb.images = [load_image("bomb.gif")]
    Shot.images = [load_image("shot.gif")]

    icon = pg.transform.scale(Alien.images[0], (32, 32))
    pg.display.set_icon(icon)
    pg.display.set_caption("Pygame Aliens")
    pg.mouse.set_visible(0)

    bgdtile = load_image("utyuu.jpg")
    background = pg.Surface(SCREENRECT.size)
    background.blit(bgdtile, (0, 0))
    screen.blit(background, (0, 0))
    pg.display.flip()

    boom_sound = load_sound("boom.wav")
    shoot_sound = load_sound("car_door.wav")
    if pg.mixer:
        music = os.path.join(main_dir, "data", "house_lo.wav")
        pg.mixer.music.load(music)
        pg.mixer.music.play(-1)

    players = pg.sprite.Group()
    aliens = pg.sprite.Group()
    shots = pg.sprite.Group()
    bombs = pg.sprite.Group()
    all = pg.sprite.RenderUpdates()
    clock = pg.time.Clock()

    global SCORE
    player = Player(all)
    alien = Alien(aliens, all)
    all.add(player.gauge)  # プレイヤーのゲージを追加
    all.add(alien.gauge)  # エイリアンのゲージを追加

    if pg.font:
        all.add(Score(all))

    while player.alive() and alien.alive():
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                return
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_f:
                    if not fullscreen:
                        print("Changing to FULLSCREEN")
                        screen_backup = screen.copy()
                        screen = pg.display.set_mode(
                            SCREENRECT.size, winstyle | pg.FULLSCREEN, bestdepth
                        )
                        screen.blit(screen_backup, (0, 0))
                    else:
                        print("Changing to windowed mode")
                        screen_backup = screen.copy()
                        screen = pg.display.set_mode(
                            SCREENRECT.size, winstyle, bestdepth
                        )
                        screen.blit(screen_backup, (0, 0))
                    pg.display.flip()
                    fullscreen = not fullscreen

        keystate = pg.key.get_pressed()
        all.clear(screen, background)
        all.update()

        direction = keystate[pg.K_RIGHT] - keystate[pg.K_LEFT]
        player.move(direction)
        player.gauge.update()
        player.gauge.increase()
        firing = keystate[pg.K_SPACE]
        if not player.reloading and firing and len(shots) < MAX_SHOTS and player.gauge.can_fire():
            Shot(player.gunpos(), shots, all)
            if pg.mixer and shoot_sound is not None:
                shoot_sound.play()
            player.gauge.current_value -= 2

        direction = keystate[pg.K_d] - keystate[pg.K_a]
        alien.move(direction)
        alien.gauge.update()
        alien.gauge.increase()
        firing = keystate[pg.K_t]
        if not alien.reloading and firing and len(bombs) < MAX_BOMBS and alien.gauge.can_fire():
            Bomb(alien.gunpos(), bombs, all)
            if pg.mixer and shoot_sound is not None:
                shoot_sound.play()
            alien.gauge.current_value -= 2
            player.gauge.current_value -= 2
        alien.reloading = firing

        for shot in pg.sprite.groupcollide(shots, aliens, True, True):
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            Explosion(shot, all)
            SCORE += 1

        for bomb in pg.sprite.spritecollide(player, bombs, 1):
            Explosion(bomb, all)
            Explosion(player, all)
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            SCORE += 1
            player.kill()

        all.add(player.gauge)  # プレイヤーのゲージを毎フレーム追加する
        all.add(alien.gauge)  # エイリアンのゲージを毎フレーム追加する

        dirty = all.draw(screen)
        pg.display.update(dirty)

        clock.tick(40)

    if pg.mixer:
        pg.mixer.music.fadeout(1000)
    pg.time.wait(1000)


if __name__ == "__main__":
    main()
    pg.quit()
