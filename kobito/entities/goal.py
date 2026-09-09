import pygame

POLE_COLOR = (225, 225, 225)
POLE_TOP_COLOR = (255, 215, 90)
FLAG_COLOR = (230, 70, 70)


class Goal(pygame.sprite.Sprite):
    """A flagpole marking the end of the level. Deliberately not solid
    (not added to the platforms group) -- the player runs straight
    through it, and Game checks for that overlap each frame to trigger
    level completion.
    """

    def __init__(self, x, ground_y, height=140):
        super().__init__()
        pole_width = 6
        flag_width = 26
        width = pole_width + flag_width

        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        pole_rect = pygame.Rect(4, 0, pole_width, height)
        pygame.draw.rect(self.image, POLE_COLOR, pole_rect)
        pygame.draw.circle(self.image, POLE_TOP_COLOR, pole_rect.midtop, 6)

        flag_points = [
            (pole_rect.right, 10),
            (pole_rect.right + flag_width, 22),
            (pole_rect.right, 34),
        ]
        pygame.draw.polygon(self.image, FLAG_COLOR, flag_points)

        self.rect = self.image.get_rect(midbottom=(x, ground_y))
