package world

import "testing"

func TestNewBoxHasWallsAndPlayer(t *testing.T) {
	w := NewBox(8, 5)

	if w.at(0, 0) != Wall {
		t.Fatal("expected wall at top-left")
	}
	if w.at(1, 1) != Player {
		t.Fatal("expected player at start")
	}
	if w.at(2, 1) != Floor {
		t.Fatal("expected floor beside player")
	}
}

func TestMoveBlockedByWall(t *testing.T) {
	w := NewBox(5, 5)
	if w.Move(-1, 0) {
		t.Fatal("expected move into wall to fail")
	}
	x, y := w.PlayerPos()
	if x != 1 || y != 1 {
		t.Fatalf("player moved unexpectedly to (%d,%d)", x, y)
	}
}

func TestMoveOntoFloor(t *testing.T) {
	w := NewBox(5, 5)
	if !w.Move(1, 0) {
		t.Fatal("expected move right to succeed")
	}
	x, y := w.PlayerPos()
	if x != 2 || y != 1 {
		t.Fatalf("expected player at (2,1), got (%d,%d)", x, y)
	}
	if w.at(1, 1) != Floor {
		t.Fatal("old tile should be floor")
	}
}
