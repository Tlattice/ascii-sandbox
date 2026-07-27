package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/gdamore/tcell/v2"
	"github.com/yourname/ascii-sandbox/features/movement"
	"github.com/yourname/ascii-sandbox/internal/world"
)

const boxWidth = 20
const boxHeight = 12

func main() {
	screen, err := tcell.NewScreen()
	if err != nil {
		fmt.Fprintf(os.Stderr, "terminal: %v\n", err)
		os.Exit(1)
	}
	if err := screen.Init(); err != nil {
		fmt.Fprintf(os.Stderr, "terminal init: %v\n", err)
		os.Exit(1)
	}
	defer screen.Fini()

	screen.SetStyle(tcell.StyleDefault)
	screen.Clear()

	w := world.NewBox(boxWidth, boxHeight)
	draw(screen, w)
	help := "arrows move  q quit"
	drawLine(screen, boxHeight+1, help)

	for {
		switch ev := screen.PollEvent().(type) {
		case *tcell.EventKey:
			if ev.Key() == tcell.KeyRune && ev.Rune() == 'q' {
				return
			}
			dir, ok := keyToDirection(ev)
			if !ok {
				continue
			}
			movement.Step(w, dir)
			screen.Clear()
			draw(screen, w)
			drawLine(screen, boxHeight+1, help)
		case *tcell.EventResize:
			screen.Sync()
			draw(screen, w)
			drawLine(screen, boxHeight+1, help)
		}
	}
}

func keyToDirection(ev *tcell.EventKey) (movement.Direction, bool) {
	switch ev.Key() {
	case tcell.KeyUp:
		return movement.Up, true
	case tcell.KeyDown:
		return movement.Down, true
	case tcell.KeyLeft:
		return movement.Left, true
	case tcell.KeyRight:
		return movement.Right, true
	default:
		return "", false
	}
}

func draw(screen tcell.Screen, w *world.World) {
	for y, line := range strings.Split(w.String(), "\n") {
		drawLine(screen, y, line)
	}
	screen.Show()
}

func drawLine(screen tcell.Screen, y int, line string) {
	for x, ch := range line {
		screen.SetContent(x, y, ch, nil, tcell.StyleDefault)
	}
}
