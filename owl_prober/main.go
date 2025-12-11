package main

import (
	"log"
	"log/slog"
	"net"

	// Import your generated protobuf package
	// Import your server package
	pb "owl_prober/proto"
	"owl_prober/server"

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
