from collections import UserList
from enum import Enum
from typing import List, Optional

import pygame
from attr import attrib, attrs

import assets
from movement import Direction, Movement
from system import SystemFlag

active = pygame.sprite.Group()


class Move(Enum):
    IDLE = (0, 0)
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    LEFT_UP = (-1, -1)
    RIGHT_UP = (1, -1)
    LEFT_DOWN = (-1, 1)
    RIGHT_DOWN = (1, 1)


controller_to_animation = {
    Move.IDLE: 'idle',
    Move.UP: 'up',
    Move.DOWN: 'down',
    Move.LEFT: 'walk',
    Move.RIGHT: 'walk',
    Move.LEFT_UP: 'walk',
    Move.RIGHT_UP: 'walk',
    Move.LEFT_DOWN: 'walk',
    Move.RIGHT_DOWN: 'walk',
}


@attrs(slots=True)
class Frame:
    surface = attrib()
    rect = attrib()

    @classmethod
    def from_frame_images(cls, frame_images, palette):
        surfaces = []
        rects = []
        for frame_image in frame_images:
            spritesheet = assets.spritesheets[frame_image.spritesheet]
            image = spritesheet.images[frame_image.image_number]
            surfaces.append(image.to_surface(palette))
            rects.append(
                pygame.Rect(
                    frame_image.x,
                    frame_image.y,
                    image.width,
                    image.height
                )
            )

        frame_rect = rects[0]
        frame_rect = frame_rect.unionall(rects[1:])
        frame_surface = pygame.Surface(frame_rect.size, pygame.SRCALPHA)
        for rect, surface in zip(rects, surfaces):
            frame_surface.blit(
                surface,
                (rect.left - frame_rect.left, rect.top - frame_rect.top),
            )
        return cls(frame_surface, frame_rect)


@attrs(slots=True, auto_attribs=True)
class Animation:
    frames: List[Frame]
    order: Optional[List[int]] = None


def make_animations(animation_definitions: dict, palette):
    def make_order(frames, order):
        if not order:
            order = list(range(len(frames)))
        return list(order)

    animations = {
        (name, Direction.RIGHT): Animation(
            frames=[
                Frame.from_frame_images(f, palette) for f in animation.frames
            ],
            order=make_order(animation.frames, animation.order),
        ) for name, animation in animation_definitions.items()
    }
    animations.update({
        (name, Direction.LEFT): Animation(
            frames=[
                Frame(
                    surface=pygame.transform.flip(frame.surface,
                                                  True,
                                                  False),
                    rect=frame.rect,
                )
                for frame in animation.frames
            ],
            order=animation.order,
        ) for (name, _), animation in animations.items()
    })
    return animations


class Graphic(pygame.sprite.Sprite):
    def __init__(self,
                 animations,
                 position,
                 palette,
                 lair,
                 direction: Direction=Direction.RIGHT,
                 groups=None) -> None:
        super().__init__(*groups)

        self.rect = pygame.Rect(position)
        self.frames = animations

        self.animations = make_animations(animations, palette)

        self.groups = groups

        self.image = self.animations['idle', Direction.RIGHT].frames[0].surface

        self.lair = lair
        self.animation_name = None
        self.has_hit = None

        self.is_attacking = False

    def get_images(self):
        animation = self.frames[self.animation_name]
        return animation[self.frame_number]


class GraphicsSystem(UserList):
    flags = SystemFlag.controller + SystemFlag.movement + SystemFlag.graphics

    def update(self):
        for entity in self.data:
            controller = entity.controller
            graphic = entity.graphics
            movement = entity.movement

            if movement.attack_frame:
                animation_name = 'swing'

                animation = graphic.animations[animation_name,
                                               movement.direction]
                if movement.attack_frame == len(animation.order) - 1:
                    graphic.is_attacking = False
                    # collide.attack.remove(graphic)

                GraphicsSystem.update_image(
                    graphic,
                    movement,
                    animation_name,
                    movement.attack_frame,
                    movement.position,
                    movement.direction,
                )

            elif entity.controller.fire:
                GraphicsSystem.update_image(
                    graphic,
                    movement,
                    'swing',
                    movement.attack_frame,
                    movement.position,
                    movement.direction,
                )
                animation = graphic.animations['swing',
                                               movement.direction]
                movement.attack_anim_length = len(animation.order)
                graphic.is_attacking = True
                # collide.attack.add(graphic)
            else:
                GraphicsSystem.move(graphic, movement, controller.direction)

    @staticmethod
    def update_image(
            graphic: Graphic,
            movement: Movement,
            animation_name: str,
            frame_num: int,
            position: pygame.Rect,
            direction):
        frame, x = GraphicsSystem.get_frame(
            graphic,
            animation_name,
            frame_num,
            position,
            direction,
        )
        GraphicsSystem.set_frame_image(
            graphic,
            animation_name,
            frame_num,
            movement,
            x,
            position.y + frame.rect.y,
            frame.rect.width,
            frame.rect.height,
            frame.surface,
        )

    @staticmethod
    def clamp_to_terrain(
            graphic: Graphic,
            current_position: pygame.Rect,
            new_position: pygame.Rect,
            frame: Frame,
            frame_num: int,
            ) -> int:
        new_rect_y = new_position.y + frame.rect.y + frame.rect.height
        if new_rect_y <= graphic.lair.terrain_object.boundary.bottom:
            return current_position.y
        return new_position.y

    @staticmethod
    def get_frame(graphic, animation_name, frame_number, position, direction):
        animation = graphic.animations[animation_name, direction]
        frame_number = animation.order[frame_number]
        frame = animation.frames[frame_number]

        # if we're facing left we want to add frame.rect.width to x
        is_facing_left = int(direction.value == Direction.LEFT.value)
        frame_width = frame.rect.width * is_facing_left
        frame_x = direction.value * (frame.rect.x + frame_width)
        x = position.x + frame_x
        return frame, x

    @staticmethod
    def set_frame_image(
            graphic,
            animation_name: str,
            frame_number: int,
            movement,
            x: int,
            y: int,
            w: int,
            h: int,
            image: pygame.Surface):
        graphic.animation_name = animation_name
        graphic.frame_number = frame_number
        movement.frame_num = frame_number
        graphic.rect.x = x
        graphic.rect.y = y
        graphic.rect.width = w
        graphic.rect.height = h
        graphic.image = image

    @staticmethod
    def move(graphic, movement, direction):
        move_frame = movement.next_frame
        new_position = movement.next_position

        animation_name = controller_to_animation[
            Move((direction.x, direction.y))
        ]

        frame, x = GraphicsSystem.get_frame(
            graphic,
            animation_name,
            move_frame,
            new_position,
            movement.direction
        )
        new_position.y = GraphicsSystem.clamp_to_terrain(
            graphic,
            movement.position,
            new_position,
            frame,
            move_frame
        )

        if movement.position == new_position:
            frame, x = GraphicsSystem.get_frame(
                graphic,
                'idle',
                0,
                new_position,
                movement.direction
            )
        else:
            movement.position = new_position
            movement.move_frame = move_frame

        GraphicsSystem.set_frame_image(
            graphic,
            animation_name,
            move_frame,
            movement,
            x,
            new_position.y + frame.rect.y,
            frame.rect.width,
            frame.rect.height,
            frame.surface,
        )


graphics_system = GraphicsSystem()
