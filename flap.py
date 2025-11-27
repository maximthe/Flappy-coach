import pygame, random, time
from pygame.locals import *

from agent_display import CoachBirdAgent, SpeechCommand

# --- Imports ---
# This file uses `pygame` for game loop, rendering and input,
# `random` to vary pipe positions, and `time` for simple delays.

# --- Game constants / configuration ---
SCREEN_WIDHT = 400
SCREEN_HEIGHT = 600
SPEED = 10
GRAVITY = 0.5
GAME_SPEED = 5

GROUND_WIDHT = 2 * SCREEN_WIDHT
GROUND_HEIGHT= 100

PIPE_WIDHT = 80
PIPE_HEIGHT = 500

PIPE_GAP = 150

# Paths to sound assets used for wing flap and hit effects
wing = 'assets/audio/wing.wav'
hit = 'assets/audio/hit.wav'

# Initialize pygame mixer for sound playback.
pygame.mixer.init()


# --- Bird sprite ---
# Represents the player-controlled bird. Handles animation frames,
# vertical movement (gravity + flap), and collision mask creation.
class Bird(pygame.sprite.Sprite):

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)

        self.images =  [pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha(),
                        pygame.image.load('assets/sprites/bluebird-midflap.png').convert_alpha(),
                        pygame.image.load('assets/sprites/bluebird-downflap.png').convert_alpha()]

        self.speed = SPEED

        self.current_image = 0
        self.image = pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)

        # Animation timing: number of milliseconds between animation frames.
        # Increase this value to slow down the wing-flap animation.
        self.animation_time = 120  # ms per frame (change to e.g. 200 for slower)
        # timestamp of last frame change
        self.last_anim_time = pygame.time.get_ticks()

        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2

    def update(self):
        # Time-based animation: only advance the frame when enough ms passed.
        now = pygame.time.get_ticks()
        if now - self.last_anim_time >= self.animation_time:
            self.current_image = (self.current_image + 1) % 3
            self.image = self.images[self.current_image]
            self.last_anim_time = now

        # Apply gravity to vertical speed and update position
        self.speed += GRAVITY
        self.rect[1] += self.speed

    def bump(self):
        self.speed = -SPEED

    def begin(self):
        # Use the same time-based animation while on the start screen
        now = pygame.time.get_ticks()
        if now - self.last_anim_time >= self.animation_time:
            self.current_image = (self.current_image + 1) % 3
            self.image = self.images[self.current_image]
            self.last_anim_time = now




# --- Pipe sprite ---
# Represents a single pipe (top or bottom). Can be created inverted (top pipe)
# and scaled to a fixed width/height; moves left at constant game speed.
class Pipe(pygame.sprite.Sprite):

    def __init__(self, inverted, xpos, ysize):
        pygame.sprite.Sprite.__init__(self)

        self. image = pygame.image.load('assets/sprites/pipe-green.png').convert_alpha()
        self.image = pygame.transform.scale(self.image, (PIPE_WIDHT, PIPE_HEIGHT))


        self.rect = self.image.get_rect()
        self.rect[0] = xpos

        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = - (self.rect[3] - ysize)
        else:
            self.rect[1] = SCREEN_HEIGHT - ysize


        self.mask = pygame.mask.from_surface(self.image)


    def update(self):
        self.rect[0] -= GAME_SPEED



# --- Ground sprite ---
# Large repeating ground image that scrolls left to simulate forward motion.
class Ground(pygame.sprite.Sprite):

    def __init__(self, xpos):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load('assets/sprites/base.png').convert_alpha()
        self.image = pygame.transform.scale(self.image, (GROUND_WIDHT, GROUND_HEIGHT))

        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT
    def update(self):
        self.rect[0] -= GAME_SPEED

# --- Utility functions ---
def is_off_screen(sprite):
    # Returns True when a sprite has moved fully off the left side of screen
    return sprite.rect[0] < -(sprite.rect[2])

def get_random_pipes(xpos):
    # Create a pair of pipes (bottom and top) with a randomized gap position
    size = random.randint(100, 300)
    pipe = Pipe(False, xpos, size)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP)
    return pipe, pipe_inverted


# --- Pygame initialization and resource loading ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))
pygame.display.set_caption('Flappy Bird')
score_font = pygame.font.SysFont('Impact', 30)
score_bg_font = pygame.font.SysFont('Impact', 32)

info_font = pygame.font.SysFont('Impact', 25)
info_1 = info_font.render("Press 'R' to try again", True, (250, 121, 88))
info_1_bg = info_font.render("Press 'R' to try again", True, (240, 234, 161))

BACKGROUND = pygame.image.load('assets/sprites/background-day.png')
BACKGROUND = pygame.transform.scale(BACKGROUND, (SCREEN_WIDHT, SCREEN_HEIGHT))
BEGIN_IMAGE = pygame.image.load('assets/sprites/message.png').convert_alpha()

# Prepare a Game Over surface to display after the bird dies
GAME_OVER_TEXT = pygame.image.load('assets/sprites/gameover.png').convert_alpha()
SCORE_PANEL = pygame.image.load('assets/sprites/score.png').convert_alpha()

# --- Sprite groups and initial objects ---
bird_group = pygame.sprite.Group()
bird = Bird()
bird_group.add(bird)

ground_group = pygame.sprite.Group()

# Create two ground pieces so we can scroll and recycle them
for i in range (2):
    ground = Ground(GROUND_WIDHT * i)
    ground_group.add(ground)

pipe_group = pygame.sprite.Group()
# Create an initial set of pipes positioned off to the right
for i in range (2):
    pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
    pipe_group.add(pipes[0])
    pipe_group.add(pipes[1])



clock = pygame.time.Clock()
agent_display = CoachBirdAgent(SCREEN_WIDHT, SCREEN_HEIGHT)

# --- Main game loop ---
# Processes input, updates sprites, spawns and recycles pipes/ground, and
# checks for collisions to end the game.

# Variables that persist across frames
begin = True
alive = True
passed = False
score = 0
high_score = 0
loss_count = 0
ticks_played = 0 #used to track how much time the player has spend playing. the counter only increment while the bird is alive
agent_enabled = False

while True:

    delta_ms = clock.tick(60)
    delta_time = delta_ms / 1000.0

    #start of new round
    if begin:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
            if event.type == KEYDOWN:
                if event.key == K_SPACE or event.key == K_UP:
                    bird.bump()
                    pygame.mixer.music.load(wing)
                    pygame.mixer.music.play()
                    begin = False
                    passed = False
                    score = 0



        screen.blit(BACKGROUND, (0, 0))
        screen.blit(BEGIN_IMAGE, (120, 150))

        if is_off_screen(ground_group.sprites()[0]):
            ground_group.remove(ground_group.sprites()[0])

            new_ground = Ground(GROUND_WIDHT - 20)
            ground_group.add(new_ground)

        bird.begin()
        ground_group.update()

        bird_group.draw(screen)
        ground_group.draw(screen)

        agent_display.update(delta_time)
        agent_display.draw(screen)

        pygame.display.update()
    #executes after the round has started
    else:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
            if event.type == KEYDOWN:
                if alive and (event.key == K_SPACE or event.key == K_UP):
                    bird.bump()
                    pygame.mixer.music.load(wing)
                    pygame.mixer.music.play()
                if not alive and not agent_display.is_speaking and event.key == K_r: # reset game
                    alive = 1
                    bird_group.empty()
                    bird = Bird()
                    bird_group.add(bird)
                    ground_group.empty()
                    for i in range (2):
                        ground = Ground(GROUND_WIDHT * i)
                        ground_group.add(ground)
                    pipe_group.empty()
                    # Create an initial set of pipes positioned off to the right
                    for i in range (2):
                        pipes = get_random_pipes(SCREEN_WIDHT * i + 800)
                        pipe_group.add(pipes[0])
                        pipe_group.add(pipes[1])
                    begin = True


        screen.blit(BACKGROUND, (0, 0))

        if (alive):
            if not begin: ticks_played += 1 # count ticks spent playing
            if is_off_screen(ground_group.sprites()[0]):
                ground_group.remove(ground_group.sprites()[0])
                new_ground = Ground(GROUND_WIDHT - 20)
                ground_group.add(new_ground)

            # increment score when the bird passes some pipes
            bird_pos = SCREEN_WIDHT / 6
            current_pipe = pipe_group.sprites()[0]
            if (passed is False) and (current_pipe.rect[0] <= bird_pos):
                passed = True
                score += 1
                print("Losses: " + str(loss_count))
                print("  Best: " + str(high_score))
                print(" Score: " + str(score))
                print("  Time: " + str(round(float(ticks_played)/60, 1)) + " seconds") # nice innit?
                print()

            if is_off_screen(pipe_group.sprites()[0]):
                pipe_group.remove(pipe_group.sprites()[0])
                pipe_group.remove(pipe_group.sprites()[0])

                pipes = get_random_pipes(SCREEN_WIDHT * 2)

                pipe_group.add(pipes[0])
                pipe_group.add(pipes[1])

                passed = False # used for counting the pipes

            bird_group.update()
            ground_group.update()
            pipe_group.update()

            bird_group.draw(screen)
            pipe_group.draw(screen)
            ground_group.draw(screen)

            agent_display.update(delta_time)
            agent_display.draw(screen)

            pygame.display.update()

            # death event
            if (pygame.sprite.groupcollide(bird_group, ground_group, False, False, pygame.sprite.collide_mask) or
                    pygame.sprite.groupcollide(bird_group, pipe_group, False, False, pygame.sprite.collide_mask)):
                pygame.mixer.music.load(hit)
                pygame.mixer.music.play()
                alive = False
                new_high_score = score > high_score
                high_score = max(high_score, score)
                if new_high_score:
                    agent_display.trigger_high_score_bounce()
                loss_count += 1
                #interface mumbo-jumbo
                score_surface = score_font.render(str(score), True,  (250, 121, 88))
                score_bg_surface = score_bg_font.render(str(score), True, (240, 234, 161))
                hs_surface = score_font.render(str(high_score), True,  (250, 121, 88))
                hs_bg_surface = score_bg_font.render(str(high_score), True, (240, 234, 161))
        if not alive:
            # overlay the Game Over text and draw the final frame then
            # player sees the result and can press 'R' to restart.
            screen.blit(GAME_OVER_TEXT, (100, 100))
            screen.blit(SCORE_PANEL, (35,200))
            screen.blit(score_bg_surface, (310,245))
            screen.blit(score_surface, (310,245))
            screen.blit(hs_bg_surface, (310,308))
            screen.blit(hs_surface, (310,308))
            screen.blit(info_1_bg, (52, 222))
            screen.blit(info_1, (50, 220))

            # check if the conditions for agent to first intervene are met
            if(not agent_enabled and loss_count >= 5 and ticks_played >=1800): # 60 ticks in a second. we check for 30 seconds of gameplay
                agent_enabled = True
                print("This is where the agent should first intervene")

            # Agent speaks to the player in between rounds
            if(agent_enabled and not agent_display.is_speaking):
                agent_display.start_speaking(SpeechCommand(duration=2.5, text="Nice run!"))

            agent_display.update(delta_time)
            agent_display.draw(screen)

            pygame.display.update()
