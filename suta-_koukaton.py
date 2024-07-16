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
ALIEN_ODDS = 22  # chances a new alien appears
BOMB_ODDS = 60  # chances a new bomb will drop
ALIEN_RELOAD = 12  # frames between new aliens
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


class Player(pg.sprite.Sprite):
    """
    Playerのイニシャライザ
    動作メソッド、
    銃の発射位置メソッドを生成しているクラス
    """

    speed = 5
    bounce = 24
    gun_offset = 0
    images: List[pg.Surface] = []

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=SCREENRECT.midbottom)
        self.reloading = 0
        self.origtop = self.rect.top
        self.facing = -1

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
        # self.frame = self.frame + 1
        # self.image = self.images[self.frame // self.animcycle % 3]


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
            
            
class Item(pg.sprite.Sprite):
    """
    ゲーム内でアイテムを表現するクラス。
    speed : int : アイテムの移動速度。
    images : List[pg.Surface] : アイテムを表現する画像のリスト。
    rect : pg.Rect : アイテムの位置とサイズを表す矩形。
    spawned : bool : アイテムが生成されたかどうかを示すフラグ。
    メソッド:
    update():アイテムの位置を更新し、画面端との衝突を処理する。
    spawn():アイテムを画面の中央に生成する。
    is_spawned() -> bool:アイテムが現在生成されているかどうかを確認する。
    collide_bombs(bombs: pg.sprite.Group) -> bool:爆弾との衝突を確認し、処理する。
    collide_shots(shots: pg.sprite.Group) -> bool:ショットとの衝突を確認し、処理する。
    reset():アイテムを初期状態にリセットする。
    """

    speed: int = 2 #itemの移動速度
    images: List[pg.Surface] = []#itemの画像リスト

    def __init__(self, *groups: pg.sprite.AbstractGroup) -> None:
        """
        Itemオブジェクトを初期化する。
        引数: *groups : pg.sprite.AbstractGroup : スプライトが所属するグループ。
        """
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = pg.transform.scale(self.images[0], (64, 48))  # 画像サイズを変更
        self.image.set_colorkey((255, 255, 255))  # 背景を透明に設定
        self.rect = self.image.get_rect(center=SCREENRECT.center)  # 矩形を取得
        self.rect.topleft = (-100, -100)  # 初期位置を画面外に設定
        self.spawned = False  # アイテムが生成されたかどうかのフラグ

    def update(self) -> None:
        """
        アイテムの位置を更新し、画面端との衝突を処理する。
        """
        if self.spawned:
            self.rect.move_ip(self.speed, 0)  # アイテムを移動
            if self.rect.top > SCREENRECT.height:
                self.kill()  # 画面外に出たらアイテムを消す
                self.spawned = False  # フラグをリセット
            if self.rect.right >= SCREENRECT.right or self.rect.left <= 0:
                self.speed = -self.speed  # 画面端に当たったら移動方向を反転

    def spawn(self) -> None:
        """
        アイテムを画面の中央に生成する。
        """
        if not self.spawned:
            self.rect.center = SCREENRECT.center  # アイテムを中央に移動
            self.spawned = True  # フラグを設定

    def is_spawned(self) -> bool:
        """
        アイテムが現在生成されているかどうかを確認する。
        戻り値: bool : アイテムが生成されていればTrue、そうでなければFalse。
        """
        return self.spawned

    def collide_bombs(self, bombs: pg.sprite.Group) -> bool:
        """
        爆弾との衝突を確認し、処理する。
        引数: bombs : pg.sprite.Group : 衝突を確認する爆弾のグループ。
        戻り値: bool : アイテムが爆弾と衝突した場合はTrue、そうでない場合はFalse。
        """
        if self.spawned:
            collided = pg.sprite.spritecollide(self, bombs, True)  # 衝突を確認
        
            if collided:
                self.kill()  # 衝突したらアイテムを消す
                self.spawned = False  # フラグをリセット
                self.rect.topleft = (-100, -100)  # 初期位置にリセット
                return True
        return False

    def collide_shots(self, shots: pg.sprite.Group) -> bool:
        """
        ショットとの衝突を確認し、処理する。
        引数: shots : pg.sprite.Group : 衝突を確認するショットのグループ。
        戻り値: bool : アイテムがショットと衝突した場合はTrue、そうでない場合はFalse。
        """
        if self.spawned:
            collided = pg.sprite.spritecollide(self, shots, True)
            if collided:
                self.kill()
                self.spawned = False  # 衝突したらフラグをリセット
                self.rect.topleft = (-100, -100)  # 画面外の初期位置にリセット
                return True
        return False

    def reset(self) -> None:
        """
        アイテムを初期状態にリセットする。
        """
        self.spawned = False # フラグをリセット
        self.rect.topleft = (-100, -100)  # 画面外に初期位置をリセット


def main(winstyle=0):
    # Initialize pygame
    if pg.get_sdl_version()[0] == 2:
        pg.mixer.pre_init(44100, 32, 2, 1024)
    pg.init()
    if pg.mixer and not pg.mixer.get_init():
        print("Warning, no sound")
        pg.mixer = None

    fullscreen = False
    winstyle = 0  # |FULLSCREEN
    bestdepth = pg.display.mode_ok(SCREENRECT.size, winstyle, 32)
    screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)

    # Load images, assign to sprite classes
    img = load_image("3.png")
    Player.images = [img, pg.transform.flip(img, 1, 0)]
    img = load_image("explosion1.gif")
    Explosion.images = [img, pg.transform.flip(img, 1, 1)]
    Alien.images = [load_image(im) for im in ("alien1.gif", "alien2.gif", "alien3.gif")]
    Bomb.images = [load_image("bomb.gif")]
    Shot.images = [load_image("shot.gif")]
    Item.images = [load_image("item.png")]  # アイテム画像を読み込む

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

    player = pg.sprite.Group()
    aliens = pg.sprite.Group()
    shots = pg.sprite.Group()
    bombs = pg.sprite.Group()
    items = pg.sprite.Group()
    all = pg.sprite.RenderUpdates()

    global SCORE
    player = Player(all)
    alien = Alien(aliens, all)
    item = Item(items, all)  # アイテムを初期化し追加

    if pg.font:
        all.add(Score(all))

    item_spawn_time = random.randint(300, 600)  # 初回のアイテム出現時間をランダムに設定 (5秒から10秒）
    item_timer = 0
    item_spawned = False

    clock = pg.time.Clock()

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
                        screen = pg.display.set_mode(SCREENRECT.size, winstyle | pg.FULLSCREEN, bestdepth)
                        screen.blit(screen_backup, (0, 0))
                    else:
                        print("Changing to windowed mode")
                        screen_backup = screen.copy()
                        screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)
                        screen.blit(screen_backup, (0, 0))
                    pg.display.flip()
                    fullscreen = not fullscreen

        keystate = pg.key.get_pressed()

        all.clear(screen, background)
        all.update()

        direction = keystate[pg.K_RIGHT] - keystate[pg.K_LEFT]
        player.move(direction)
        firing = keystate[pg.K_SPACE]
        if not player.reloading and firing and len(shots) < MAX_SHOTS:
            Shot(player.gunpos(), shots, all)
            if pg.mixer and shoot_sound is not None:
                shoot_sound.play()
        player.reloading = firing

        direction = keystate[pg.K_d] - keystate[pg.K_a]
        alien.move(direction)
        firing = keystate[pg.K_t]
        if not alien.reloading and firing and len(bombs) < MAX_BOMBS:
            Bomb(alien.gunpos(), bombs, all)
            if pg.mixer and shoot_sound is not None:
                shoot_sound.play()
        alien.reloading = firing
        
        for shot in pg.sprite.spritecollide(alien, shots, 1):
            Explosion(shot, all)
            Explosion(alien, all)
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            alien.kill()

        for bomb in pg.sprite.spritecollide(player, bombs, 1):
            Explosion(bomb, all)
            Explosion(player, all)
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            player.kill()

        item_timer += 1# アイテム生成タイマーを更新
        if not item_spawned and item_timer >= item_spawn_time:
            item.spawn()  # アイテムを生成
            item_spawned = True

        # アイテムが爆弾と衝突したかを確認
        if item.collide_bombs(bombs):
            item_timer = 0
            item_spawn_time = random.randint(300, 600)  # 新しいアイテム出現時間を設定
            item = Item(items, all)  # アイテムを初期化し再度作成
            item_spawned = False
        
        if item.collide_shots(shots):
            item_timer = 0
            item_spawn_time = random.randint(300, 600)  # 新しいアイテム出現時間を設定
            item = Item(items, all)  # アイテムを初期化し再度作成
            item_spawned = False
        
        pg.display.update(all.draw(screen))

        clock.tick(40)

    if pg.mixer:
        pg.mixer.music.fadeout(1000)
    pg.time.wait(1000)

if __name__ == "__main__":
    main()
    pg.quit()
