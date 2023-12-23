import numpy as np
from threading import Thread
from random import choice
from keyboard import is_pressed
from msvcrt import getch, kbhit
from time import sleep, perf_counter
from os import system

class Vec2:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __add__(self, B: "Vec2"):
        return Vec2(self.x + B.x, self.y + B.y)

    def __radd__(self, B: "Vec2"):
        return self.__add__(B)

    def __eq__(self, B: "Vec2"):
        return self.x == B.x and self.y == B.y
    
    def __neg__(self):
        return Vec2(-self.x, -self.y)
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def set(self, B: "Vec2"):
        self.x = B.x
        self.y = B.y
    
    def abs(self):
        return Vec2(abs(self.x), abs(self.y))
    
    def copy(self):
        return Vec2(self.x, self.y)

UP = Vec2(0,-1)
RIGHT = Vec2(1,0)
INPUT_MAPPINGS = {
     "w" : UP,    "a" : -RIGHT,    "s" : -UP,     "d" : RIGHT, 
    "up" : UP, "left" : -RIGHT, "down" : -UP, "right" : RIGHT, 
}

class Game:
    def __init__(self, map_size: Vec2 = Vec2(17, 17), apples: int = 1, frame_rate: int = 0.2):
        self.map_size = map_size
        self.empty_cells = [Vec2(x, y) for y in range(self.map_size.y) for x in range(self.map_size.x)]
        self.player = Player(Vec2(1, map_size.y // 2), self.empty_cells)
        self.apple_spawn = Vec2(map_size.x - 2, map_size.y // 2)
        self.apples = [Apple(self.apple_spawn, self.empty_cells) for x in range(min(apples, self.map_size.x * self.map_size.y))]
        # Levittää ylimääräiset omenat satunnaisesti
        for apple in self.apples[1:]:
            apple.regeneratePosition()
            apple.updateEmptyCells()
        self.entities =  self.apples + [self.player]
        self.frame_rate = frame_rate
        self.score = 0
        self.game_over = False
        self.renderer = Renderer(self)
    
    def isGameOver(self):
        return self.player.isCollidingBorder(self.map_size) or self.player.isCollidingSelf() or self.game_over
    
    def start(self):
        system('cls')
        input_output = Vec2(1,0)
        thread_kill = [False]
        input_thread = Thread(target=threadedMovementInput, args=(input_output, thread_kill, self))
        input_thread.start()
        while not self.game_over:
            self.update(input_output)
        thread_kill[0] = True
        input_thread.join()

    def end(self):
        self.game_over = True

    def update(self, player_direction: Vec2):
        frame_start = perf_counter()
        self.player.direction = Vec2(player_direction.x, player_direction.y)
        self.player.move()
        if self.isGameOver() or self.player.length >= self.map_size.x * self.map_size.y:
            self.end()
        for apple in self.apples:
            self.score += apple.tryConsume(self.player)
        if not self.game_over:
            self.renderer.updateBuffer()
            """ Tyhjien solujen debugaus
            for x in range(self.map_size.x):
                for y in range(self.map_size.y):
                    if Vec2(x, y) not in self.empty_cells:
                        self.renderer.buffer[x][y] = "[" + self.renderer.buffer[x][y][1] + "]"
            """
            self.renderer.erase()
            self.renderer.drawBuffer()
            sleep(max(self.frame_rate - (perf_counter() - frame_start), 0)) # Tasoittaa kuvien välistä odotus aikaa suoritusajan perusteella
        
    def saveScore(self, name: str):
        with open("scoreboard.txt", "r") as file:
            lines = file.readlines()
            score_string = f"{self.score} {self.map_size.x * self.map_size.y} {repr(name)}\n"
            found = False
            for i, line in enumerate(lines):
                if int(line[:line.find(" ")]) < self.score or len(line) == 0:
                    lines.insert(i, score_string)
                    found = True
                    break
            if not found:
                lines.append(score_string)
        if len(lines) > 10:
            del lines[-1]
        with open("scoreboard.txt", "w") as file:
            file.writelines(lines)

class GUI:
    def __init__(self):
        self.game = None

    def startMenu(self):
        system("cls")
        print("""\b   
   _________         _________
  /         \       /         \\
 /  /~~~~~\  \     /  /~~~~~\  \\
 |  |     |  |     |  |     |  |
 |  |     |  |     |  |     |  |
 |  |     |  |     |  |     |  |         /
 |  |     |  |     |  |     |  |       //
(o  o)    \  \_____/  /     \  \_____/ /
 \__/      \         /       \        /
  |         ~~~~~~~~~         ~~~~~~~~
  ^
------------------------------------------
        Press any key to continue
""")
        waitForAnyKey()
        self.setupMenu()
        self.startGame()
        self.endMenu()

    def setupMenu(self):
        system("cls")
        map_size = None
        while not map_size or len(map_size) != 2:
            try:
                map_size = [max(int(x), 5) for x in input("Map size (min 5, 5) (x, y): ").split(",")]
            except:
                pass
            system("cls")
        self.game = Game(Vec2(map_size[0], map_size[1]))
    
    def endMenu(self):
        system("cls")
        print(f"score: {self.game.score}")
        self.game.saveScore(input("Enter name: "))
        self.scoreboard()

    def scoreboard(self):
        system("cls")
        print("Rank Score Map Name")
        with open("scoreboard.txt", "r") as file:
            for i, line in enumerate(file.readlines()):
                print(f"{i + 1}.", line.replace("\'", "").replace('\"', ""), end="")
        print("press any key to return to menu")
        waitForAnyKey()
        self.startMenu()
    
    def startGame(self):
        system("cls")
        self.game.renderer.cycle()
        waitForAnyKey()
        self.game.start()


class Renderer:

    def __init__(self, game: Game):
        self.game = game
        self.buffer = np.array([["   "] * game.map_size.y] * game.map_size.x, dtype = str)

    def clearBuffer(self, buffer: np.ndarray):
        buffer.fill("   ")
    
    def updateBuffer(self):
        for entity in self.game.entities:
            entity.rasterize(self.buffer)

    def drawBuffer(self):
        print("\n".join(["".join(i) for i in np.pad(np.swapaxes(self.buffer, 1, 0), pad_width = 1, mode = 'constant', constant_values = "░░░")]))
    
    def erase(self):
        print("\033[F" * (self.game.map_size.y*2 + 2 + 1))

    def cycle(self):
        self.updateBuffer()
        self.erase()
        self.drawBuffer()

# Entities

class Player:
    def __init__(self, position: Vec2, empty_cells: list[Vec2]):
        self.char_set = {
                       UP : " ║ ",          -UP : " ║ ",         RIGHT : "═══",      -RIGHT  : "═══",
             (UP, -RIGHT) : "═╗ ",  (UP, RIGHT) : " ╔═",  (-RIGHT, UP) : " ╚═",  (RIGHT, UP) : "═╝ ",
            (-UP, -RIGHT) : "═╝ ", (-UP, RIGHT) : " ╚═", (-RIGHT, -UP) : " ╔═", (RIGHT, -UP) : "═╗ "
        }
        self.position = position
        self.direction = Vec2(1,0)
        self.length = 2
        self.cache = [(position, self.direction)]
        self.has_grown = True # Pysyy totena seuraavaan rasterize kutsuun saakka
        self.empty_cells = empty_cells
    
    def move(self):
        self.position += self.direction
        self.cache.append((self.position, self.direction))
        if len(self.cache) > self.length + 1:
            del self.cache[0]
        self.updateEmptyCells()

    def grow(self):
        self.length += 1
        self.has_grown = True
    
    def isCollidingBorder(self, map_size: Vec2):
        return self.position.x < 0 or self.position.x >= map_size.x or self.position.y < 0 or self.position.y >= map_size.y
    
    def isCollidingSelf(self):
        for position, direction in self.cache[:-1]:
            if position == self.position:
                return True
        return False
    
    def rasterize(self, buffer: list[list]):
        if not self.has_grown:
            target_old = self.cache[0][0]
            buffer[target_old.x][target_old.y] = "   "
        buffer[self.position.x][self.position.y] = self.char_set[self.direction]
        if len(self.cache) > 2 and self.direction != self.cache[-2][1]:
            target = self.cache[-2][0]
            buffer[target.x][target.y] = self.char_set[(self.cache[-2][1], self.direction)]
        self.has_grown = False
    
    def updateEmptyCells(self):
        if not self.has_grown:
            target_old = self.cache[0][0]
            if target_old not in self.empty_cells:
                self.empty_cells.append(target_old.copy())
        try:
            self.empty_cells.remove(self.position)
        except:
            pass
        
class Apple:
    def __init__(self, position: Vec2, empty_cells: list[Vec2]):
        self.char = " ■ "
        self.position = position.copy()
        self.prev_position = position.copy()
        self.has_regenerated = True
        self.empty_cells = empty_cells

    def tryConsume(self, player: Player):
        if player.position == self.position:
            player.grow()
            self.regeneratePosition()
            self.updateEmptyCells()
            return 1
        return 0
    
    def regeneratePosition(self):
        self.prev_position = self.position.copy()
        if len(self.empty_cells) != 0:
            self.position = choice(self.empty_cells).copy()
    
    def rasterize(self, buffer: list[list]):
        if self.has_regenerated:
            buffer[self.prev_position.x][self.prev_position.y] = "   "
        buffer[self.position.x][self.position.y] = self.char + " "
        self.has_regenerated = False

    def updateEmptyCells(self, clear_prev: bool = False):
        if clear_prev and not self.prev_position in self.empty_cells:
            self.empty_cells.append(self.prev_position.copy())
        try:
            self.empty_cells.remove(self.position)
        except:
            pass

# Input

def whichKeysPressed(*keys: list[str]):
    pressed = []
    for key in keys:  
        if is_pressed(key):
            pressed.append(key)
    return pressed

def waitForAnyKey():
    while not kbhit():
        continue
    getch()

def threadedMovementInput(output: Vec2, kill: list[bool], game: Game):
    while not kill[0]:
        if output == game.player.direction:
            keys = whichKeysPressed("w", "a", "s", "d", "up", "down", "left", "right")
            new_direction = game.player.direction
            for key in keys:
                key_direction = INPUT_MAPPINGS[key]
                if key_direction.abs() != game.player.direction.abs():
                    new_direction = key_direction
            output.set(new_direction)

gui = GUI()
gui.startMenu()