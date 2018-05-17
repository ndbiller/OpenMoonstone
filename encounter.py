import copy

import assets
import graphics
from assets.manager import Manager
from audio import AudioSystem, Audio
from blood import BloodSystem
from collide import Collider, Collision, CollisionSystem
from controller import Controller, ControllerSystem, player_one, player_two
from entity import Entity
from extract import extract_palette
from graphics import Graphic, GraphicsSystem
from logic import Logic, LogicSystem
from movement import Movement, MovementSystem
from piv import PivFile
from state import AnimationState, AnimationStateSystem
from system import SystemFlag


def change_player_colour(colour: str, palette: list):
    colours = {
        'blue': [0xa, 0x7, 0x4],
        'orange': [0xf80, 0xc50, 0xa30],
        'green': [0x8c6, 0x593, 0x251],
        'red': [0xf22, 0xb22, 0x700],
        'black': [0x206, 0x103, 1],
    }
    palette = copy.deepcopy(palette)
    old_palette = extract_palette(palette, base=256)
    # palette[0xc // 2:0xc // 2 + 2] = colours[colour]
    palette[6:8] = colours[colour]
    new_palette = extract_palette(palette, base=256)

    # This is the blood colour, which is an incorrect orange in new_pallete
    # investigate in ida if this gets overrriden later
    new_palette[15] = old_palette[15]
    return PivFile.make_palette(new_palette)


def create_player(colour: str, x: int, y: int, lair, control_map, sprite_groups):
    controller = Controller(control_map)
    movement = Movement((x, y))

    palette = change_player_colour(
        colour,
        assets.files.backgrounds[lair.background].extracted_palette,
    )
    graphic = Graphic(
        animations=assets.animation.knight,
        position=movement.position,
        palette=palette,
        lair=lair,
        groups=sprite_groups,
    )
    collider = Collision(
        collider=Collider(assets.animation.knight, assets.collide_hit),
    )
    logic = Logic()

    knight = Entity(
        controller=controller,
        movement=movement,
        graphics=graphic,
        collision=collider,
        logic=logic,
        state=AnimationState(),
        audio=Audio(sounds=assets.animation.knight),
    )

    return knight


class Encounter:
    def __init__(self):
        self.asset_manager = Manager([assets.animation.knight])
        self.lair = assets.lairs[0]

        self.audio_system = AudioSystem(assets=self.asset_manager)
        self.blood_system = BloodSystem()
        self.collision_system = CollisionSystem()
        self.controller_system = ControllerSystem()
        self.graphics_system = GraphicsSystem()
        self.logic_system = LogicSystem()
        self.movement_system = MovementSystem()
        self.state_system = AnimationStateSystem()


        blue = create_player('blue', 100, 100, self.lair, player_one, [self.graphics_system.active])
        self.register_entity(blue)
        red = create_player('red', 200, 150, self.lair, player_two, [self.graphics_system.active])
        self.register_entity(red)

    def register_entity(self, entity):
        systems = {
            SystemFlag.audio: self.audio_system,
            SystemFlag.blood: self.blood_system,
            SystemFlag.controller: self.controller_system,
            SystemFlag.state: self.state_system,
            SystemFlag.movement: self.movement_system,
            SystemFlag.graphics: self.graphics_system,
            SystemFlag.collision: self.collision_system,
            SystemFlag.logic: self.logic_system,
        }

        for flag, system in systems.items():
            if flag in entity.flags:
                system.append(entity)

    def destroy_entites(self):
        systems = {
            SystemFlag.audio: self.audio_system,
            SystemFlag.blood: self.blood_system,
            SystemFlag.controller: self.controller_system,
            SystemFlag.state: self.state_system,
            SystemFlag.movement: self.movement_system,
            SystemFlag.graphics: self.graphics_system,
            SystemFlag.collision: self.collision_system,
            SystemFlag.logic: self.logic_system,
        }
        entities = [e for e in state_system if e.state.value == State.destroy]
        for entity in entities:
            for flag, system in systems.items():
                if flag in entity.flags:
                    system.remove(entity)