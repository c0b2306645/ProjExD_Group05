#!/usr/bin/env python
import os
import random
from typing import List

# import basic pygame modules
import pygame as pg

# see if we can load more than standard BMP
if not pg.image.get_extended():
    raise SystemExit("Sorry, extended image module required")


# game constants
MAX_SHOTS = 1  # most player bullets onscreen
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
    Playerのイニシャライザ
    動作メソッド、
    銃の発射位置メソッドを生成しているクラス
    """

    speed = 5
    gun_offset = 0
    images: List[pg.Surface] = []

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
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
        # self.rect.top = self.origtop - (self.rect.left // self.bounce % 2)

    def gunpos(self):
        pos = self.facing * self.gun_offset + self.rect.centerx
        return pos, self.rect.top


class Alien(pg.sprite.Sprite):
    """
    エイリアンのイニシャライザ
    動作メソッド
    銃の発射位置メソッド
    エイリアンの位置更新メソッドを生成しているクラス
    """
    
    speed = 5
    gun_offset = 0
    images: List[pg.Surface] = []

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
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
        #self.rect.move_ip(self.facing, 0)
        if not SCREENRECT.contains(self.rect):
            self.facing = -self.facing
            self.rect = self.rect.clamp(SCREENRECT)


class Explosion(pg.sprite.Sprite):
    """
    オブジェクトが衝突した際に爆発する演出を作成するクラス
    """

    defaultlife = 12
    animcycle = 3
    images: List[pg.Surface] = []

    def __init__(self, actor, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(center=actor.rect.center)
        self.life = self.defaultlife

    def update(self):
        """
        called every time around the game loop.

        Show the explosion surface for 'defaultlife'.
        Every game tick(update), we decrease the 'life'.

        Also we animate the explosion.
        """
        self.life = self.life - 1
        self.image = self.images[self.life // self.animcycle % 2]
        if self.life <= 0:
            self.kill()


class Shot(pg.sprite.Sprite):
    """
    Playerが使う銃を生成するクラス
    """

    speed = -10
    images: List[pg.Surface] = []

    def __init__(self, pos, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=pos)

    def update(self):
        """
        called every time around the game loop.

        Every tick we move the shot upwards.
        """
        self.rect.move_ip(0, self.speed)
        if self.rect.top <= 0:
            self.kill()


class Bomb(pg.sprite.Sprite):
    """
    Alienが落とす爆弾を生成するクラス
    """

    speed = 10
    images: List[pg.Surface] = []

    def __init__(self, alien_pos,*groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midtop=alien_pos)

    def update(self):
        """
        - make an explosion.
        - remove the Bomb.
        """
        self.rect.move_ip(0, self.speed)
        if self.rect.bottom >= SCREENRECT.bottom:
            self.kill()


class Score(pg.sprite.Sprite):
    """
    状況に応じて増減し、MAX_GUNSとMAX_BOMBSに関与するスコアクラス
    """

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.font = pg.font.Font(None, 20)
        self.font.set_italic(1)
        self.color = "white"
        self.lastscore = -1
        self.update()
        self.rect = self.image.get_rect().move(10, 450)

    def update(self):
        """We only update the score in update() when it has changed."""
        if SCORE != self.lastscore:
            self.lastscore = SCORE
            msg = f"Score: {SCORE}"
            self.image = self.font.render(msg, 0, self.color)


def main(winstyle=0):
    # Initialize pygame
    if pg.get_sdl_version()[0] == 2:
        pg.mixer.pre_init(44100, 32, 2, 1024)
    pg.init()
    if pg.mixer and not pg.mixer.get_init():
        print("Warning, no sound")
        pg.mixer = None

    fullscreen = False
    # Set the display mode
    winstyle = 0  # |FULLSCREEN
    bestdepth = pg.display.mode_ok(SCREENRECT.size, winstyle, 32)
    screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)

    # Load images, assign to sprite classes
    # (do this before the classes are used, after screen setup)
    img = load_image("3.png")
    Player.images = [img, pg.transform.flip(img, 1, 0)]
    img = load_image("explosion1.gif")
    Explosion.images = [img, pg.transform.flip(img, 1, 1)]
    Alien.images = [load_image(im) for im in ("alien1.gif", "alien2.gif", "alien3.gif")]
    Bomb.images = [load_image("bomb.gif")]
    Shot.images = [load_image("shot.gif")]

    # decorate the game window
    icon = pg.transform.scale(Alien.images[0], (32, 32))
    pg.display.set_icon(icon)
    pg.display.set_caption("Pygame Aliens")
    pg.mouse.set_visible(0)

    # create the background, tile the bgd image ここで背景変更
    bgdtile = load_image("utyuu.jpg")
    background = pg.Surface(SCREENRECT.size)
    background.blit(bgdtile, (0, 0))
    screen.blit(background, (0, 0))
    pg.display.flip()

    # load the sound effects
    boom_sound = load_sound("boom.wav")
    shoot_sound = load_sound("car_door.wav")
    if pg.mixer:
        music = os.path.join(main_dir, "data", "house_lo.wav")
        pg.mixer.music.load(music)
        pg.mixer.music.play(-1)

    # Initialize Game Groups
    players = pg.sprite.Group()
    aliens = pg.sprite.Group()
    shots = pg.sprite.Group()
    bombs = pg.sprite.Group()
    all = pg.sprite.RenderUpdates()
    clock = pg.time.Clock()

    # initialize our starting sprites
    global SCORE
    player = Player(all)
    
    alien = Alien(aliens, all)

    all.add(player.gauge)  # プレイヤーのゲージを追加
    all.add(alien.gauge)  # エイリアンのゲージを追加

    
    if pg.font:#ここでスコア表示
        all.add(Score(all))

    while player.alive() and alien.alive():
        # get input
        for event in pg.event.get():  # もし双方のうち片方が死んだら数秒勝利画面を作る
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

        # clear/erase the last drawn sprites
        all.clear(screen, background)

        # update all the sprites
        all.update()

        # handle player input
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
        player.reloading = firing

        # Alien Shot and Drop bombs
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
        alien.reloading = firing

        # Detect collisions between aliens and players.
        for alien in pg.sprite.groupcollide(aliens, shots, 1, 1).keys():
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            Explosion(alien, all)
        

        # See if alien bombs hit the player.
        for bomb in pg.sprite.spritecollide(player, bombs, 1):
            Explosion(bomb, all)
            Explosion(player, all)
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            SCORE += 1
            player.kill()
        
        all.add(player.gauge)  # プレイヤーのゲージを毎フレーム追加する
        all.add(alien.gauge)  # エイリアンのゲージを毎フレーム追加する


        # draw the scene
        dirty = all.draw(screen)
        pg.display.update(dirty)

        # cap the framerate at 40fps. Also called 40HZ or 40 times per second.
        clock.tick(40)
        
    if pg.mixer:
        pg.mixer.music.fadeout(1000)
    pg.time.wait(1000)


# call the "main" function if running this script
if __name__ == "__main__":
    main()
    pg.quit()  