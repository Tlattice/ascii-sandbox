package movement

import (
	"path/filepath"
	"runtime"
	"testing"

	"github.com/yourname/ascii-sandbox/internal/world"
)

func TestReplayMatchesSnapshot(t *testing.T) {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed")
	}
	dir := filepath.Dir(file)

	replay, err := LoadReplay(filepath.Join(dir, "replay.json"))
	if err != nil {
		t.Fatalf("load replay: %v", err)
	}

	want, err := LoadSnapshot(filepath.Join(dir, "snapshot.txt"))
	if err != nil {
		t.Fatalf("load snapshot: %v", err)
	}

	w := world.NewBox(replay.Width, replay.Height)
	Replay(w, replay.Steps)

	if got := w.String(); got != want {
		t.Fatalf("snapshot mismatch\n got:\n%s\n want:\n%s", got, want)
	}
}

func TestStepIntoWall(t *testing.T) {
	w := world.NewBox(5, 5)
	x0, y0 := w.PlayerPos()

	if Step(w, Up) {
		t.Fatal("expected step into wall to fail")
	}
	x1, y1 := w.PlayerPos()
	if x0 != x1 || y0 != y1 {
		t.Fatalf("player moved from (%d,%d) to (%d,%d)", x0, y0, x1, y1)
	}
}
