package input

import (
	"testing"

	"github.com/yourname/ascii-sandbox/features/movement"
)

func TestReplaySource(t *testing.T) {
	src := NewReplay([]movement.Direction{movement.Right, movement.Down})

	dir, ok := src.Next()
	if !ok || dir != movement.Right {
		t.Fatalf("first step: got (%q, %v)", dir, ok)
	}

	dir, ok = src.Next()
	if !ok || dir != movement.Down {
		t.Fatalf("second step: got (%q, %v)", dir, ok)
	}

	_, ok = src.Next()
	if ok {
		t.Fatal("expected replay to end")
	}
}
