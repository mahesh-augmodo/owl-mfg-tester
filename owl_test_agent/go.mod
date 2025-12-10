module owl_test_agent

go 1.24.0

require (
	google.golang.org/grpc v1.64.0 // Use latest stable version
	google.golang.org/protobuf v1.34.2 // Current version
)

require (
	github.com/holoplot/go-evdev v0.0.0-20250804134636-ab1d56a1fe83
	golang.org/x/image v0.23.0
	periph.io/x/conn/v3 v3.7.2
	periph.io/x/devices/v3 v3.7.4
	periph.io/x/host/v3 v3.8.3
)

require (
	github.com/prometheus/procfs v0.19.2 // indirect
	golang.org/x/net v0.22.0 // indirect
	golang.org/x/sys v0.37.0 // indirect
	golang.org/x/text v0.21.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20240318140521-94a12d6c2237 // indirect
)
