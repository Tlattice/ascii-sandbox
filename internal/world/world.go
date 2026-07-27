package world

import "strings"

const (
	Wall   = '#'
	Floor  = '.'
	Player = '@'
)

type World struct {
	width, height      int
	tiles              []rune
	playerX, playerY   int
}

func NewBox(width, height int) *World {
	if width < 3 || height < 3 {
		panic("box must be at least 3x3")
	}

	w := &World{
		width:  width,
		height: height,
		tiles:  make([]rune, width*height),
	}

	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			if x == 0 || y == 0 || x == width-1 || y == height-1 {
				w.set(x, y, Wall)
			} else {
				w.set(x, y, Floor)
			}
		}
	}

	w.playerX = 1
	w.playerY = 1
	w.set(w.playerX, w.playerY, Player)
	return w
}

func (w *World) Width() int  { return w.width }
func (w *World) Height() int { return w.height }

func (w *World) PlayerPos() (int, int) {
	return w.playerX, w.playerY
}

func (w *World) set(x, y int, ch rune) {
	w.tiles[y*w.width+x] = ch
}

func (w *World) at(x, y int) rune {
	return w.tiles[y*w.width+x]
}

func (w *World) CanMove(dx, dy int) bool {
	nx, ny := w.playerX+dx, w.playerY+dy
	if nx < 0 || ny < 0 || nx >= w.width || ny >= w.height {
		return false
	}
	return w.at(nx, ny) == Floor
}

func (w *World) Move(dx, dy int) bool {
	if !w.CanMove(dx, dy) {
		return false
	}
	w.set(w.playerX, w.playerY, Floor)
	w.playerX += dx
	w.playerY += dy
	w.set(w.playerX, w.playerY, Player)
	return true
}

func (w *World) String() string {
	lines := make([]string, w.height)
	for y := 0; y < w.height; y++ {
		start := y * w.width
		lines[y] = string(w.tiles[start : start+w.width])
	}
	return strings.Join(lines, "\n")
}
