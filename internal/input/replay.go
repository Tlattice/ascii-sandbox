package input

import "github.com/yourname/ascii-sandbox/features/movement"

// Source yields movement directions. Returns ok=false when input is exhausted
// or the player requests quit.
type Source interface {
	Next() (movement.Direction, bool)
}

// Replay feeds a fixed list of directions, for deterministic tests and playback.
type Replay struct {
	steps []movement.Direction
	index int
}

func NewReplay(steps []movement.Direction) *Replay {
	return &Replay{steps: steps}
}

func (r *Replay) Next() (movement.Direction, bool) {
	if r.index >= len(r.steps) {
		return "", false
	}
	dir := r.steps[r.index]
	r.index++
	return dir, true
}

func ParseDirection(name string) (movement.Direction, bool) {
	switch movement.Direction(name) {
	case movement.Up, movement.Down, movement.Left, movement.Right:
		return movement.Direction(name), true
	default:
		return "", false
	}
}
