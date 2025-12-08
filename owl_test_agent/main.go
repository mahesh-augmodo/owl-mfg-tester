package main

import (
	"fmt"
	"log"
	"log/slog"
	"net"
	"strings"

	// Import your generated protobuf package
	// Import your server package
	pb "owl_test_agent/proto"
	"owl_test_agent/server"
	"owl_test_agent/util"

	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

const (
	port = ":50051" // The port your gRPC server will listen on
)

func main() {
	// 1. Set up a listener for incoming TCP connections
	lis, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatalf("failed to listen on port %s: %v", port, err)
	}
	slog.SetLogLoggerLevel(slog.LevelDebug)
	// Check if battery is present.
	var cw221X util.BatteryDetails
	cw221X.DeviceName = "cw221X-bat"
	err = util.UpdateBatteryReadings(&cw221X)
	if err != nil {
		slog.Error("unable to read battery parameters", err)
	}
	slog.Info("Battery readings", "parameters", &cw221X)
	input_devices, err := util.FindInputDevices()
	if err != nil {
		slog.Warn("Unable to find Input devices :", "err", err)
	}
	for _, device := range input_devices {
		if device.DeviceType == "accelerometer" {
			duration := 5
			go func() {
				slog.Info(fmt.Sprintf("Counting events on %s over %d(s)", device.DeviceName, duration))
				event_report, err := util.CountEventsOverDuration(device.SysfsPath, duration)
				if err != nil {
					fmt.Printf("Unable to count events: %v", err)
				}
				split_events := strings.Split(event_report, "\n")
				slog.Info(fmt.Sprintf("Event Count: %d", len(split_events)))
				// for _, event := range split_events {
				// 	slog.Debug(event)
				// }
			}()
		}
	}
	// 2. Create a new gRPC server instance
	grpcServer := grpc.NewServer()
	reflection.Register(grpcServer)
	// 3. Create an instance of your custom Server implementation from the 'server' package.
	//    NewServer now initializes AgentVersion and DeviceId internally.
	serverInstance := server.NewServer()

	// 4. Register your service implementation with the gRPC server
	pb.RegisterDutAgentServiceServer(grpcServer, serverInstance)

	log.Printf("DutAgentService server listening at %v", lis.Addr())
	// The detailed log message for Agent Version and Device ID is now handled by server.NewServer()

	// 5. Start serving gRPC requests
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("failed to serve gRPC server: %v", err)
	}
}
