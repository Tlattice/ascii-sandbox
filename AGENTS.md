# AGENT RULES

## General

- Keep functions under 100 lines.
- Keep files under 200 lines.
- Keep packages cohesive.
- Prefer composition.
- Never introduce global state.

## Every feature must include

- implementation
- tests
- replay
- snapshot
- contract

## Before finishing

go test ./...
go test -race ./...
go vet ./...
