package movement

import (
	"encoding/json"
	"os"
	"strings"
)

type ReplayFile struct {
	Width  int         `json:"width"`
	Height int         `json:"height"`
	Steps  []Direction `json:"steps"`
}

func LoadReplay(path string) (ReplayFile, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return ReplayFile{}, err
	}
	var replay ReplayFile
	if err := json.Unmarshal(data, &replay); err != nil {
		return ReplayFile{}, err
	}
	return replay, nil
}

func LoadSnapshot(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return strings.TrimRight(string(data), "\n"), nil
}
