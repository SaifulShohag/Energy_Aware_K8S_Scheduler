build:
	go build -o bin/scheduler ./cmd/scheduler/main.go

docker:
	docker build -t my-scheduler:local .

tidy:
	go mod tidy
