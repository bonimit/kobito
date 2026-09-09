class Animation:
    """Cycles through a list of frame Surfaces at a fixed rate.

    This is deliberately dumb: it doesn't know about characters or game
    state, just "given these frames and this speed, which one is
    current right now." Player decides *when* to switch animations
    (idle/run/jump); this class just plays whichever one is active.
    """

    def __init__(self, frames, frame_duration=0.15, loop=True):
        self.frames = frames
        self.frame_duration = frame_duration
        self.loop = loop
        self.timer = 0.0
        self.index = 0

    def reset(self):
        self.timer = 0.0
        self.index = 0

    def update(self, dt):
        self.timer += dt
        while self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.index += 1
            if self.index >= len(self.frames):
                self.index = 0 if self.loop else len(self.frames) - 1

    @property
    def current_frame(self):
        return self.frames[self.index]
