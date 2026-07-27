package movement

import (
	"github.com/yourname/ascii-sandbox/internal/world"
)

type Direction string

const (
	Up    Direction = "up"
	Down  Direction = "down"
	Left  Direction = "left"
	Right Direction = "right"
)

func Step(w *world.World, dir Direction) bool {
	switch dir {
	case Up:
		return w.Move(0, -1)
	case Down:
		return w.Move(0, 1)
	case Left:
		return w.Move(-1, 0)
	case Right:
		return w.Move(1, 0)
	default:
		return false
	}
}

func Replay(w *world.World, steps []Direction) {
	for _, dir := range steps {
		Step(w, dir)
	}
}
